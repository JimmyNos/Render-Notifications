# This file is part of the Render Notifications plugin
# https://github.com/JimmyNos/Render-Notifications
# Copyright (c) 2023 Michael Mosako.
# 
# This program is free software: you can redistribute it and/or modify  
# it under the terms of the GNU General Public License as published by  
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU 
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>.

#bl_info = {
#    "name": "Render Notifications",
#    "author": "Michael Mosako (JimmyNoStar)",
#    "version": (1, 0, 0),
#    "blender": (4, 3, 2),
#    "location": "Render properties",
#    "description": "Sends webhooks, discord and desktop notifications to notify you when your render starts, finishes, or is canceled.",
#    "wiki_url": "https://github.com/JimmyNos/Render-Notifications",
#    "category": "Render"
#}

import time
import bpy

from bpy.types import Operator, AddonPreferences,PropertyGroup,Panel
from bpy.props import StringProperty, IntProperty, BoolProperty
from bpy.app.handlers import persistent

import sys, subprocess, os, site, platform
import json
import shutil
import requests
import math

from datetime import datetime

import discord
from notifypy import Notify as NotifyClass
from discord import Webhook as DiscordWebhookClass, Embed as DiscordEmbedClass
Notify = NotifyClass
DiscordWebhook = DiscordWebhookClass
DiscordEmbed = DiscordEmbedClass

import asyncio
import aiohttp

# Define the addon preferences class
class RenderNotificationsPreferences(AddonPreferences):
    bl_idname = __package__
    
    ## Desktop ##
    custom_sound: BoolProperty( #type: ignore
        name="Use Custom sound file",
        description="Use a custom file for desktop notifications.",
        default=False,
    )
    desktop_sound_path: StringProperty( #type: ignore
        name="Path to sound file",
        description="Use a custom '.wav' audio file for desktop notification sound.",
        subtype = "FILE_PATH",
        options = {"LIBRARY_EDITABLE"},
        maxlen = 1024
    )
    
    ## Discord ##
    discord_webhook_name: StringProperty( #type: ignore
        name="channel webhook name",
        description="Name of discord bot that will send the notifications. Note: will use the name set in the discord channel webhook settings if this is left empty."
    )
    discord_webhook_url: StringProperty( #type: ignore
        name="Discord channel webhook url",
        description="Discord channel webhook url to send notifications to."
    )
    tmp_output_path: StringProperty( #type: ignore
        name="Default temporary output path",
        description="Default temporary save location for previewed renders that are sent to discord.",
        subtype = "FILE_PATH",
        options = {"LIBRARY_EDITABLE"},
        default = "C:/tmp/",
        maxlen = 1024
    )

    ## Third-party Webhook ##
    third_party_webhook_url: StringProperty( #type: ignore
        name="Third-party webhook url",
        description="Third-party webhook url to send notifications to."
    )
    third_party_simple_every_frame_message: StringProperty( #type: ignore
        name="Third-party webhook On-Every-frame",
        description="Simple message to send each time a frame is rendered on every frame render besides start, first, completion and cancel.",
        default="Frame rendered."
    )
    third_party_simple_start_message: StringProperty( #type: ignore
        name="Third-party webhook On-Start",
        description="Simple message to send once the render has started.",
        default="Render started."
    )
    third_party_simple_first_message: StringProperty( #type: ignore
        name="Third-party webhook On-First",
        description="Simple message to send once the first frame has rendered.",
        default="First Frame Rendered."
    )
    third_party_simple_completion_message: StringProperty( #type: ignore
        name="Third-party webhook On-Completion",
        description="Simple message to send on the once the render completed.",
        default="Render Completed."
    )
    third_party_simple_cancel_message: StringProperty( #type: ignore
        name="Third-party webhook On-Cancel",
        description="Simple message to send on render cancellation.",
        default="Render Canceled."
    )
    
    # Drawing UI for addon preferences
    def draw(self, context):
        layout = self.layout
        layout.label(text="Setup Notifications")
        
        ## Desktop ##
        desktop_box = layout.box()
        row = desktop_box.row()
        desktop_box.label(text="Desktop Notifications")
        row = desktop_box.row()
        row.label(text="Custom Sound:")
        row.prop(self, "custom_sound", text="",placeholder="custom_sound.wav")
        row = desktop_box.row()
        row.label(text="Sound Path:")
        row.prop(self, "desktop_sound_path", text="")
        
        ## Discord ##
        discord_box = layout.box()
        row = discord_box.row()
        discord_box.label(text="Discord Notifications")
        row = discord_box.row()
        row.label(text="Discord Channel Webhook Name:")
        row.prop(self, "discord_webhook_name", text="")
        row = discord_box.row()
        row.label(text="Discord Channel Webhook url:")
        row.prop(self, "discord_webhook_url", text="")
        row = discord_box.row()
        row.label(text="Default Temporary Save Location:")
        row.prop(self, "tmp_output_path", text="")

        ## Third-party Webhook ##
        third_party_webhook_box = layout.box()
        row = third_party_webhook_box.row()
        third_party_webhook_box.label(text="Third-party Webhook Notifications")
        row = third_party_webhook_box.row()
        row.label(text="Third-party Webhook url:")
        row.prop(self, "third_party_webhook_url", text="")
        
        # simple messages #
        third_party_webhook_box.label(text="")
        row = third_party_webhook_box.row()
        third_party_webhook_box.label(text="Send Simplified Webhook Notifications")
        
        # on every frame
        row = third_party_webhook_box.row()
        row.label(text="Message On Every Frame Rendered:")
        row.prop(self, "third_party_simple_every_frame_message", text="")
        # on render start
        row = third_party_webhook_box.row()
        row.label(text="Message On Render Start:")
        row.prop(self, "third_party_simple_start_message", text="")
        # on first frame
        row = third_party_webhook_box.row()
        row.label(text="Message On First Frame Rendered:")
        row.prop(self, "third_party_simple_first_message", text="")
        # on render completion
        row = third_party_webhook_box.row()
        row.label(text="Message On Render Completion:")
        row.prop(self, "third_party_simple_completion_message", text="")
        # on render cancel
        row = third_party_webhook_box.row()
        row.label(text="Message On Render Cancellation:")
        row.prop(self, "third_party_simple_cancel_message", text="")
        

# Update function for webhook settings
def update_third_party_webhook_every_frame(self, context):
    """Toggle all third-party webhook settings when 'notify on every frame' is toggled"""
    state = self.third_party_webhook_every_frame
    self.third_party_webhook_start = state
    self.third_party_webhook_first = state
    self.third_party_webhook_completion = state
    self.third_party_webhook_cancel = state

# Define a property group to hold the render notifications properties
class Render_Notifications_Properties(PropertyGroup):
    #enable notifications
    enable_notifications: bpy.props.BoolProperty(
        name="Enable notifications",  # This will appear as the checkbox label
        description="Enable render notifications.",
        default=False
    ) # type: ignore
    
    #desktop notifications
    desktop_start: bpy.props.BoolProperty(
        name="Desktop notify on start",
        description="Send desktop notifications when the render job starts.",
        default=False  # Starts unchecked
    ) # type: ignore
    desktop_first: bpy.props.BoolProperty(
        name="Desktop notify on first",
        description="Send desktop notifications when the first frame has rendered.",
        default=False  # Starts unchecked
    )# type: ignore
    desktop_completion: bpy.props.BoolProperty(
        name="Desktop notify on completion",
        description="Send desktop notifications when the render job is complete.",
        default=False  # Starts unchecked
    )# type: ignore
    desktop_cancel: bpy.props.BoolProperty(
        name="Desktop notify on cancel",
        description="Send desktop notifications when the render job is canceled.",
        default=False  # Starts unchecked
    )# type: ignore
    
    #discord notifications
    discord_preview: bpy.props.BoolProperty(
        name="Discord notify with preview",
        description="Send the first and final frame to discord for an animation job, or a still image when a still render job is complete complete. Note: the default save location for the preview is set in the addon preferences. if the output extension is openEXR or the size of the frame/still is larger than discord's allowed attachment size (with or without nitro), no preview will be sent.",
        default=False  # Starts unchecked
    ) # type: ignore
    use_custom_preview_path: bpy.props.BoolProperty(
        name="Use custom preview path",
        description="Use a custom path for the previewed renders that are sent to discord. Note: the default save location for the preview is set in the addon preferences and will be used if this is unchecked.",
        default=False  # Starts unchecked
    ) # type: ignore
    discord_preview_path: bpy.props.StringProperty( #type: ignore
        name="Desktop notify preview file",
        description="Custom path save location for previewed renders that are sent to discord.",
        subtype = "FILE_PATH",
        options = {"LIBRARY_EDITABLE"},
        default = "C:/tmp/",
        maxlen = 1024
    )
    
    #Third-party webhook notifications
    third_party_webhook_every_frame: bpy.props.BoolProperty(
        name="Third-party webhook notify on every frame",
        description="Send third-party webhook notifications on every frame.",
        default=False,  # Starts unchecked
        update=update_third_party_webhook_every_frame
    ) # type: ignore
    third_party_webhook_start: bpy.props.BoolProperty(
        name="Third-party webhook notify on start",
        description="Send third-party webhook notifications when the render job starts.",
        default=False  # Starts unchecked
    ) # type: ignore
    third_party_webhook_first: bpy.props.BoolProperty(
        name="Third-party webhook notify on first",
        description="Send third-party webhook notifications when the first frame has rendered.",
        default=False  # Starts unchecked
    )# type: ignore
    third_party_webhook_completion: bpy.props.BoolProperty(
        name="Third-party webhook notify on completion",
        description="Send third-party webhook notifications when the render job is complete.",
        default=False  # Starts unchecked
    )# type: ignore
    third_party_webhook_cancel: bpy.props.BoolProperty(
        name="Third-party webhook notify on cancel",
        description="Send third-party webhook notifications when the render job is canceled.",
        default=False  # Starts unchecked
    )# type: ignore
    
    # simple message
    simple_message: bpy.props.BoolProperty(
        name="simple message",
        description="Send a simple message on each render stage (start, first frame, completion and cancel)",
        default=False  # Starts unchecked
    )# type: ignore
    # send simplified render data
    simple_render_data: bpy.props.BoolProperty(
        name="simplified render data",
        description="attach simplified render data to simplified notifications. Data sent: project name, job type, total frames, frame range, first frame time, render time and est. render time.",
        default=False  # Starts unchecked
    )# type: ignore
    # use custom message payload
    custom_message: bpy.props.BoolProperty(
        name="Custom simple message",
        description="Set custom message for each render stage. By default, it uses the messages set in the addon preferences.",
        default=False  # Starts unchecked
    )# type: ignore
    on_every: bpy.props.StringProperty( #type: ignore
        name="On Every Frame",
        description="Simple message to send each time a frame is rendered on every frame render besides start, first, completion and cancel.",
        default = ""
    )
    on_start: bpy.props.StringProperty( #type: ignore
        name="On start",
        description="Simple message to send once the render has started.",
        default = ""
    )
    on_first_frame: bpy.props.StringProperty( #type: ignore
        name="On first frame",
        description="Simple message to send once the first frame has rendered.",
        default = ""
    )
    on_completion: bpy.props.StringProperty( #type: ignore
        name="On completion",
        description="Simple message to send on the once the render completed.",
        default = ""
    )
    on_cancel: bpy.props.StringProperty( #type: ignore
        name="On cancel",
        description="Simple message to send on render cancellation.",
        default = ""
    )
    
    
    # Desktop, Discord and third-party Webhook toggle properties
    is_desktop: bpy.props.BoolProperty(
        name="desktop notifications",  # This will appear as the checkbox label
        description="Enable desktop notifications.",
        default=False
    )# type: ignore
    
    is_discord: bpy.props.BoolProperty(
        name="discord notifications",  # This will appear as the checkbox label
        description="Enable discord notifications.",
        default=False
    )# type: ignore

    is_third_party_webhook: bpy.props.BoolProperty(
        name="third-party webhook notifications",  # This will appear as the checkbox label
        description="Enable third-party webhook notifications.",
        default=False
    )# type: ignore
    is_simple_third_party_webhook: bpy.props.BoolProperty(
        name="simplified third-party webhook notifications",  # This will appear as the checkbox label
        description="Enable simplified third-party webhook notifications instead of a raw json payload.",
        default=False
    )# type: ignore

class RenderNotificationsPanel:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

# create UI elements for addon properties in the render properties tab
class RENDER_PT_Notifications(RenderNotificationsPanel, Panel):
    """Creates a notifications panel in the render properties tab"""
    bl_label = "Render Notifications"
    bl_idname = "RENDER_PT_Notifications"
    
    def draw_header(self,context):
        scene = context.scene
        props = scene.render_panel_props
        layout = self.layout
        layout.prop(props, "enable_notifications", text="", icon="INTERNET") 

    # Drawing addon UI in the render properties panel
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.render_panel_props 
        layout.enabled = props.enable_notifications

class RENDER_PT_Desktop_Notifications(RenderNotificationsPanel, Panel):
    bl_label = "Desktop Notifications"
    bl_parent_id = "RENDER_PT_Notifications"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw_header(self,context):
        scene = context.scene
        props = scene.render_panel_props
        layout = self.layout
        layout.enabled = props.enable_notifications
        layout.prop(props, "is_desktop", text="") 
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.use_property_split = True
        layout.use_property_decorate = False
        props = scene.render_panel_props 
        layout.enabled = props.is_desktop and props.enable_notifications
        
        # notification properties for desktop notifications
        #desktop_box = layout.box()
        
        # If checkbox is enabled, show additional settings for desktop notifications
        desktop_col = layout.column()
        desktop_col.label(text="Configure Desktop Notifications:")
        desktop_col.prop(props, "desktop_start", text="Notify On Start")
        desktop_col.prop(props, "desktop_first", text="Notify On First")
        desktop_col.prop(props, "desktop_completion", text="Notify On Completion")
        desktop_col.prop(props, "desktop_cancel", text="Notify On Cancel")
            
class RENDER_PT_Discord_Notifications(RenderNotificationsPanel, Panel):
    bl_label = "Discord Notifications"
    bl_parent_id = "RENDER_PT_Notifications"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw_header(self,context):
        scene = context.scene
        props = scene.render_panel_props
        layout = self.layout
        layout.enabled = props.enable_notifications
        layout.prop(props, "is_discord", text="") 
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.use_property_split = True
        layout.use_property_decorate = False
        props = scene.render_panel_props 
        layout.enabled = props.is_discord and props.enable_notifications
        
        # notification properties for discord notifications
        #discord_box = layout.box()
        discord_col = layout.column()
        discord_col.label(text="Configure Discord Notifications:")
        discord_col.prop(props, "discord_preview", text="Send Previews")
        discord_col.prop(props, "use_custom_preview_path", text="Use Custom Preview Path")
        discord_col.prop(props, "discord_preview_path", text="Previews Save Location") 

class RENDER_PT_Webhook_Notifications(RenderNotificationsPanel, Panel):
    bl_label = "Third Party Webhook Notifications"
    bl_parent_id = "RENDER_PT_Notifications"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw_header(self,context):
        scene = context.scene
        props = scene.render_panel_props
        layout = self.layout
        layout.enabled = props.enable_notifications
        layout.prop(props, "is_third_party_webhook", text="") 
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.use_property_split = True
        layout.use_property_decorate = False
        props = scene.render_panel_props 
        layout.enabled = props.is_third_party_webhook and props.enable_notifications
        
        # notification properties for webhook notifications
        #third_party_webhook_box = layout.box()
        
        third_party_webhook_col = layout.column()
        third_party_webhook_col.label(text="Configure Third-party Notifications:")
        third_party_webhook_col.prop(props, "third_party_webhook_every_frame", text="Notify On Every Frame")
        third_party_webhook_col.prop(props, "third_party_webhook_start", text="Notify On Start")
        third_party_webhook_col.prop(props, "third_party_webhook_first", text="Notify On First")
        third_party_webhook_col.prop(props, "third_party_webhook_completion", text="Notify On Completion")
        third_party_webhook_col.prop(props, "third_party_webhook_cancel", text="Notify On Cancel")

class RENDER_PT_Simplified_Webhook_Notifications(RenderNotificationsPanel, Panel):
    bl_label = "Simplified Notifications"
    bl_parent_id = "RENDER_PT_Webhook_Notifications"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw_header(self,context):
        scene = context.scene
        props = scene.render_panel_props
        layout = self.layout
        layout.enabled = props.enable_notifications and props.is_third_party_webhook
        layout.prop(props, "is_simple_third_party_webhook", text="") 
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.use_property_split = True
        layout.use_property_decorate = False
        props = scene.render_panel_props 
        layout.enabled = props.is_simple_third_party_webhook and props.enable_notifications and props.is_third_party_webhook
        
        # notification properties for simplified webhook notifications
        #third_party_webhook_box = layout.box()
        
        third_party_webhook_col = layout.column()
        third_party_webhook_col.label(text="Configure Simplified Notifications:")
        third_party_webhook_col.prop(props, "simple_render_data", text="Attach Simplified Render Data")
        third_party_webhook_col.prop(props, "custom_message", text="Custom Messages")
        third_party_webhook_col.prop(props, "on_every", text="Every Frame")
        third_party_webhook_col.prop(props, "on_start", text="Start")
        third_party_webhook_col.prop(props, "on_first_frame", text="First Frame")
        third_party_webhook_col.prop(props, "on_completion", text="Completion")
        third_party_webhook_col.prop(props, "on_cancel", text="Cancel")


# RenderNotifier class to handle the rendering notifications logic
class RenderNotifier:
    def __init__(self):
        self.blend_filepath = None
        self.blend_filename = None
        self.is_animation = False
        self.total_frames = 0
        self.average_est_frames = []
        self.RENDER_START_TIME = None
        self.RENDER_PRE_TIME = None
        self.RENDER_TOTAL_TIME = None
        self.RENDER_FIRST_FRAME = None
        self.RENDER_CURRENT_FRAME = None
        self.RENDER_CANCELLED_TIME = None
        self.average_time = 0
        self.job_type = ""
        self.blender_data = {}
        self.current_frame = None
        self.counter = 0
        self.precountdown = 0.0
        self.message_id = None
        
        self.frame_step = 1
        
        self.file = None
        self.no_preview = False
        self.rendered_frame_path = ""
        self.file_extension = ".png"
        
        self.discord_preview = False
        self.desktop_cancel = False
        self.third_party_webhook_cancel = False
        self.third_party_webhook_every_frame = False
        self.is_discord = False
        self.is_third_party_webhook = False
        self.is_desktop = False
        self.tmp_output_path = ""
        self.final_path = ""
        self.first_rendered_frame_path = ""
        self.final_first_path = ""
        self.tmp_output_name = ""
        self.tmp_output_name_frist = ""
        
        self.is_less_than = False
        self.is_skip_frame = False
        self.skip_frame = 0
        self.skip_frame_counter = 0
        
        self.isfirst_frame = False
        
        self.is_response_received = False
        
        self.p = None
    
    # reset variables on render initialization
    # this is called when the render job starts
    def clean_var(self):
        self.is_animation = False
        self.total_frames = 0
        self.average_est_frames = []
        self.RENDER_START_TIME = None
        self.RENDER_PRE_TIME = None
        self.RENDER_TOTAL_TIME = None
        self.RENDER_FIRST_FRAME = None
        self.RENDER_CURRENT_FRAME = None
        self.RENDER_CANCELLED_TIME = None
        self.average_time = 0
        self.job_type = ""
        self.blender_data = {}
        self.current_frame = None
        self.counter = 0
        self.precountdown = 0.0
        
        self.tmp_output_name = ""
        self.tmp_output_name_frist = ""

    # handle discord webhook using a separate thread-safe event loop
    def send_webhook_non_blocking(self, init=False, frame=False,isfirstframe=False, finished=False, canceled=False,blender_data=None):
        current_frame_time = getattr(self, 'current_frame_time', 0.0)
        current_frame = self.current_frame
        is_last_frame = current_frame == self.total_frames
        # Dynamic frame skipping logic to avoid filling up STDIN buffer
        if not init and not isfirstframe and not finished and not canceled and not is_last_frame:  
            if current_frame_time <= 1.0: # if frame time is less than 1 second
                self.is_less_than = True
            else:
                self.is_less_than = False
            
            # Adjust skip frame settings based on current frame time
            if self.is_less_than and not self.is_skip_frame: # if frame time is less than 1 second and not already skipping frames
                self.is_skip_frame = True
                self.skip_frame = math.ceil(1.0 / current_frame_time) # calculate how many frames to skip (rounding up)
                print(f"Will skip {self.skip_frame} frames to avoid filling up STDIN buffer. frame time: {current_frame_time}")
            elif self.is_less_than and self.is_skip_frame:
                print(f"Skipping frame {current_frame} to avoid filling up STDIN buffer. frame time: {current_frame_time}")
                #return
            else:
                self.is_skip_frame = False
                self.skip_frame = 0
                self.skip_frame_counter = 0
                print("Not skipping frames anymore. frame time:", current_frame_time)
            
            # Skip frame logic
            if self.skip_frame_counter < self.skip_frame:
                self.skip_frame_counter += 1
                print(f"Skipping frame {current_frame} ({self.skip_frame_counter}/{self.skip_frame})")
                return
            elif self.skip_frame_counter == self.skip_frame and self.is_skip_frame:
                print(f"stop skipping frames: frame {current_frame} ({self.skip_frame_counter}/{self.skip_frame})")
                self.skip_frame_counter = 0
                self.is_skip_frame = False
                #return
                # proceed to send data
            #elif self.skip_frame_counter > self.skip_frame:
            #    #self.skip_frame_counter = 0
            #    print("Not skipping frames anymore")
            
        try:
            if blender_data is None:
                blender_data = self.blender_data

            start_timer = time.time()
            print("Sending data to subprocess:", blender_data)
            try:
                s = json.dumps(blender_data) + "\n"
                # Ensure subprocess exists and stdin is writable before writing
                if not self.p:
                    print("⚠️ Subprocess handle is None. Skipping write.")
                elif self.p.poll() is not None:
                    print(f"⚠️ Subprocess has exited (returncode={self.p.returncode}). Skipping write.")
                elif not hasattr(self.p, "stdin") or self.p.stdin is None or self.p.stdin.closed:
                    print("⚠️ Subprocess stdin is closed or unavailable. Skipping write.")
                else:
                    try:
                        self.p.stdin.write(s)
                        self.p.stdin.flush()
                        print("Written to subprocess stdin:")
                        print("Flushed subprocess stdin.")
                    except BrokenPipeError as e:
                        print(f"BrokenPipeError writing to subprocess: {e} (errno={getattr(e,'errno',None)})")
                        try:
                            err = self.p.stderr.read()
                            if err:
                                print("Subprocess stderr:", err.strip())
                        except Exception as re:
                            print(f"Error reading subprocess stderr after BrokenPipeError: {re}")
                    except OSError as e:
                        print(f"OSError writing to subprocess: {e} (errno={getattr(e,'errno',None)})")
                        try:
                            err = self.p.stderr.read()
                            if err:
                                print("Subprocess stderr:", err.strip())
                        except Exception as re:
                            print(f"Error reading subprocess stderr after OSError: {re}")
                    except Exception as e:
                        print(f"Unexpected error writing to subprocess: {type(e).__name__}: {e}")

            except Exception as e:
                print(f"⚠️ Error occurred while preparing data to write to subprocess: {e}")

            #print("Data sent to subprocess, waiting for response...")
            # Read response
            #out_line = self.p.stdout.readline()
            #print("Response received from subprocess:", out_line)
            #print("\n\n")
            ## Check for EOF
            #if not out_line:
            #    print("No response (EOF).")
            ## process the response
            #try:
            #    parsed = json.loads(out_line.strip())
            #    #self.is_response_received = True
            #    print("Response:", parsed)
            #except Exception:
            #    print("Error parsing JSON response: (raw)", out_line.strip())

            try:
                if finished or canceled:
                    # Send exit command
                    self.p.stdin.close()
                    ret = self.p.wait(timeout=0.1)
                    err = self.p.stderr.read()
                    print("Process finished. returncode=", ret)
                    if err:
                        print("Stderr:", err.strip())
            except Exception as e:
                print(f"Error closing subprocess: {e}")
            print(f"✅ Successfully ran writing subprocess in {time.time() - start_timer} seconds")
        except Exception as e:
            print(f"⚠️ Error occurred while running writing subprocess: {e}")

    # Handle render logic
    @persistent
    def render_init(self,scene,*args):
        self.clean_var() # clears the variables for a new render job
        addon_name = __package__
        
        self.is_libs_installed = bpy.context.preferences.addons[addon_name].preferences.is_installed = True

        #get blend file name
        self.blend_filepath = bpy.data.filepath
        self.blend_filename = os.path.basename(self.blend_filepath) if self.blend_filepath else "Untitled.blend"
        self.blend_filename = self.blend_filename[:-6] # slice off the .blend extension
        self.tmp_output_name = self.blend_filename
        self.tmp_output_name_frist = self.blend_filename + " first frame"
        
        self.RENDER_START_TIME = datetime.now()
        self.blender_data['render_start_countdown'] = self.render_start_countdown = time.time()
        
        self.total_frames = bpy.context.scene.frame_end - bpy.context.scene.frame_start + 1
        self.frame_step  = bpy.context.scene.frame_step if bpy.context.scene.frame_step > 0 else 1
        #self.total_frames = self.total_frames / self.frame_step
        
        self.blender_data["call_type"] = "render_init"
        self.blender_data["project_name"] = self.blend_filename
        self.blender_data["total_frames"] = self.total_frames
        self.blender_data["total_frames_stepped"] = round(self.total_frames / self.frame_step)
        self.blender_data["frame_step"] = self.frame_step
        self.blender_data["is_frame_step"] = True if self.frame_step > 1 else False
        
        ## Desktop ##
        self.is_custom_sound = bpy.context.preferences.addons[addon_name].preferences.custom_sound
        self.desktop_sound_path = bpy.context.preferences.addons[addon_name].preferences.desktop_sound_path
        self.is_desktop = bpy.context.scene.render_panel_props.is_desktop
        self.desktop_start = bpy.context.scene.render_panel_props.desktop_start
        self.desktop_first = bpy.context.scene.render_panel_props.desktop_first
        self.desktop_completion = bpy.context.scene.render_panel_props.desktop_completion
        self.desktop_cancel = bpy.context.scene.render_panel_props.desktop_cancel
        
        ## Discord ##
        # Check if the user wants to use a custom preview path
        if bpy.context.scene.render_panel_props.use_custom_preview_path:
            custom_path = bpy.context.scene.render_panel_props.discord_preview_path
            if os.path.isdir(custom_path):
                self.tmp_output_path = custom_path
            else:
                print(f"⚠️ Invalid or inaccessible custom preview path: {custom_path}. Using default path.")
                self.tmp_output_path = bpy.context.preferences.addons[addon_name].preferences.tmp_output_path
            self.tmp_output_path = bpy.context.scene.render_panel_props.discord_preview_path
        else:
            self.tmp_output_path = bpy.context.preferences.addons[addon_name].preferences.tmp_output_path
            
        self.first_rendered_frame_path = bpy.context.preferences.addons[addon_name].preferences.tmp_output_path
        self.discord_webhook_name = bpy.context.preferences.addons[addon_name].preferences.discord_webhook_name
        self.discord_webhook_url = bpy.context.preferences.addons[addon_name].preferences.discord_webhook_url
        self.is_discord = bpy.context.scene.render_panel_props.is_discord
        self.discord_preview = bpy.context.scene.render_panel_props.discord_preview
        
        if self.is_discord:
            print("Starting process...")
            self.blender_data["discord_webhook_url"] = self.discord_webhook_url
            self.blender_data["discord_webhook_name"] = self.discord_webhook_name
            self.blender_data["discord_preview"] = self.discord_preview
            self.blender_data["first_rendered_frame_path"] = self.first_rendered_frame_path
            # Use sys.executable and the addon path to ensure we run the project's sub.py
            addon_dir = os.path.dirname(__file__)
            discord_process = os.path.join(addon_dir, "discord_process.py")
            
            # Parent process environment variables
            parent_env = os.environ.copy()
            # Add the parent's sys.path to the PYTHONPATH environment variable
            parent_env['PYTHONPATH'] = os.pathsep.join(sys.path)
            
            # Use -u for unbuffered output so we can stream
            self.p = subprocess.Popen(
                [sys.executable, "-u", discord_process],
                env=parent_env,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        
        ## Webhook ##
        self.third_party_webhook_url = bpy.context.preferences.addons[addon_name].preferences.third_party_webhook_url
        self.is_third_party_webhook = bpy.context.scene.render_panel_props.is_third_party_webhook
        self.third_party_webhook_every_frame = bpy.context.scene.render_panel_props.third_party_webhook_every_frame
        self.third_party_webhook_start = bpy.context.scene.render_panel_props.third_party_webhook_start
        self.third_party_webhook_first = bpy.context.scene.render_panel_props.third_party_webhook_first
        self.third_party_webhook_completion = bpy.context.scene.render_panel_props.third_party_webhook_completion
        self.third_party_webhook_cancel = bpy.context.scene.render_panel_props.third_party_webhook_cancel
        
        self.is_simple_third_party_webhook = bpy.context.scene.render_panel_props.is_simple_third_party_webhook
        self.is_third_party_simple_render_data = bpy.context.scene.render_panel_props.simple_render_data
        self.is_third_party_custom_message = bpy.context.scene.render_panel_props.custom_message
        
        # default to preferences messages
        self.third_party_on_every = bpy.context.preferences.addons[addon_name].preferences.third_party_simple_every_frame_message
        self.third_party_on_start = bpy.context.preferences.addons[addon_name].preferences.third_party_simple_start_message
        self.third_party_on_first_frame = bpy.context.preferences.addons[addon_name].preferences.third_party_simple_first_message
        self.third_party_on_completion = bpy.context.preferences.addons[addon_name].preferences.third_party_simple_completion_message
        self.third_party_on_cancel = bpy.context.preferences.addons[addon_name].preferences.third_party_simple_cancel_message
        
        # if custom messages aren't empty
        if self.is_third_party_custom_message:
            if not bpy.context.scene.render_panel_props.on_start == "":
                self.third_party_on_every = bpy.context.scene.render_panel_props.on_every
                
            if not bpy.context.scene.render_panel_props.on_start == "":
                self.third_party_on_start = bpy.context.scene.render_panel_props.on_start
                
            if not bpy.context.scene.render_panel_props.on_first_frame == "":
                self.third_party_on_first_frame = bpy.context.scene.render_panel_props.on_first_frame
                
            if not bpy.context.scene.render_panel_props.on_completion == "":
                self.third_party_on_completion = bpy.context.scene.render_panel_props.on_completion
                
            if not bpy.context.scene.render_panel_props.on_cancel == "":
                self.third_party_on_cancel = bpy.context.scene.render_panel_props.on_cancel

    # Handle render pre logic render_start_countdown
    @persistent
    def render_pre(self,scene,*args):
        #print("\nPre Render\n")
        self.current_frame = bpy.context.scene.frame_current
        #self.blender_data["frame"] = bpy.context.scene.frame_current
        self.blender_data["isfirst_frame"] = self.current_frame == bpy.context.scene.frame_start
        self.isfirst_frame = self.current_frame == bpy.context.scene.frame_start
        # check if the render job is an animation or a still image 
        if self.current_frame == bpy.context.scene.frame_start:
            self.is_animation = True
            self.job_type = "Animation"  
            self.blender_data["job_type"] = self.job_type
            self.blender_data["frame"] = bpy.context.scene.frame_current
            self.blender_data["frame_range"] = f"{bpy.context.scene.frame_start} - {bpy.context.scene.frame_end}"
            self.blender_data["Total_frames_to_render"] = self.total_frames / self.frame_step
            print(f"Current frame: {self.current_frame} {self.blender_data['frame']} {bpy.context.scene.frame_current}")    
            
            if self.is_discord:
                self.send_webhook_non_blocking(init=True,blender_data=self.blender_data)
                #self.blender_data["discord_webhook_url"] = "cleared" # clear webhook url after init

            if self.is_third_party_webhook and self.third_party_webhook_start:
                self.send_third_party_webhook()
              
            if self.is_desktop and self.desktop_start:
                self.notify_desktop(
                    title="Render started", 
                    message="Render job started for: " + self.blender_data["project_name"]
                    )
        
        # if the current frame is not the first frame, it is a still image render job
        elif self.current_frame != bpy.context.scene.frame_start and self.is_animation == False:
            #is_animation = False
            self.job_type = "Still"
            self.blender_data["job_type"] = self.job_type
            self.blender_data["frame"] = bpy.context.scene.frame_current
            if self.is_discord:
                self.send_webhook_non_blocking(init=True,blender_data=self.blender_data)
            
            if self.is_third_party_webhook and self.third_party_webhook_start:
                self.send_third_party_webhook()
                
            if self.is_desktop and self.desktop_start:
                self.notify_desktop(
                    title="Render started", 
                    message="Render job started for: " + self.blender_data["project_name"]
                    )
        
    # Handle render post logic
    @persistent   
    def render_post(self,scene,*args):
        #print("\nPost Render\n")
        
        # Track call type for logging or webhook purposes
        self.blender_data["call_type"] = "render_post"
        self.current_frame = scene.frame_current
        current_frame = scene.frame_current
        is_first_frame = self.current_frame == scene.frame_start
        stepped_frames = self.total_frames / self.frame_step
        
        try:
            if self.is_animation:
                # Check if this is the first frame of the animation
                #is_first_frame = self.current_frame == scene.frame_start
                #current_frame = scene.frame_start
                print(f"Animation render - Current frame: {self.current_frame} {current_frame}, First frame: {is_first_frame}")
                
                if is_first_frame:
                    print("First frame rendered.")
                    self.RENDER_FIRST_FRAME = datetime.now() - self.RENDER_START_TIME
                    
                    # Estimate average time per frame and total job duration
                    self.precountdown = time.time() - self.render_start_countdown
                    self.current_frame_time = self.precountdown
                    self.countdown = int(time.time() + self.precountdown * (stepped_frames - self.counter))
                    self.current_countdown = int(time.time() + self.precountdown)
                    self.precountdown = time.time()
                    
                    self.average_est_frames.append(self.RENDER_FIRST_FRAME)
                    self.RENDER_PRE_TIME = datetime.now()
                    self.counter += 1
                    
                    # Populate render info for sending to Discord or display
                    self.blender_data["frame"] = current_frame
                    self.blender_data["RENDER_FIRST_FRAME"] = str(self.RENDER_FIRST_FRAME)[:-4]
                    self.blender_data["est_render_job"] = str(self.RENDER_FIRST_FRAME * (stepped_frames - self.counter))[:-4]
                    self.blender_data["frames_left"] = f"{stepped_frames - self.counter}"
                    self.blender_data["frames_rendered"] = self.counter
                    self.blender_data["rendered_frames_percentage"] = round((self.counter / stepped_frames * 100),2)
                    self.blender_data["countdown"] = f"<t:{self.countdown}:R>"
                    self.blender_data["next_frame_countdown"] = f"<t:{self.current_countdown}:R>"
                    
                    if self.discord_preview and self.is_discord: # save first frame if discord preview is enabled
                        first_filename = self.tmp_output_name_frist + self.file_extension
                        self.blender_data['final_first_path'] = self.final_first_path = os.path.join(self.first_rendered_frame_path, first_filename)
                    
                        
                        def delayed_first_frame_save():
                            # Prefer copying the file that Blender wrote to disk (most reliable).
                            self.blender_data["frame"] = current_frame
                            self.blender_data["isfirst_frame"] = True
                            try:
                                src = getattr(self, 'rendered_frame_path', None)
                                print(f"Rendered frame path: {src}")
                                if src and os.path.isfile(src):
                                    os.makedirs(os.path.dirname(self.final_first_path), exist_ok=True)
                                    shutil.copy2(src, self.final_first_path)
                                    print(f"✅ First frame copied from: {src} -> {self.final_first_path}")
                                    self.send_webhook_non_blocking(frame=True,isfirstframe=True,blender_data=self.blender_data)
                                    return None
                            except Exception as e:
                                print(f"⚠️ Failed to copy first frame: {e}")
                            
                            image = bpy.data.images.get('Render Result')
                            if image and image.has_data:
                                try:
                                    os.makedirs(os.path.dirname(self.final_first_path), exist_ok=True)
                                    image.save_render(self.final_first_path)
                                    print(f"✅ First frame saved to: {self.final_first_path}")
                                    self.send_webhook_non_blocking(frame=True,isfirstframe=True,blender_data=self.blender_data)
                                except Exception as e:
                                    print(f"❌ Failed to save first frame (render_post): {e}")
                                    self.blender_data['no_first_preview'] = self.no_first_preview = True
                                    print(f"⚠️ First frame preview not available. ({self.blender_data['no_first_preview']})")
                                    self.send_webhook_non_blocking(frame=True,isfirstframe=True,blender_data=self.blender_data)
                            else:
                                print("⚠️ Render Result not available for first frame. (render_post)")
                            return None

                        bpy.app.timers.register(delayed_first_frame_save, first_interval=0.2)   
                    elif self.is_discord and not self.discord_preview:
                        try:
                            self.send_webhook_non_blocking(frame=True,isfirstframe=True,blender_data=self.blender_data)
                        except Exception as e:
                            print(f"error in re_post when sending first frame discord: {e}")
                # if not the first frame
                else:
                    try:
                        # Time per frame and ETA calculations
                        self.precountdown = time.time() - self.precountdown
                        self.current_frame_time = self.precountdown
                        self.countdown = int(time.time() + self.precountdown * (stepped_frames - self.counter))
                        self.current_countdown = int(time.time() + self.precountdown)
                        self.counter += 1
                        self.RENDER_CURRENT_FRAME = datetime.now() - self.RENDER_PRE_TIME
                        self.average_est_frames.append(self.RENDER_CURRENT_FRAME) 
                        self.RENDER_PRE_TIME = datetime.now()
                        self.precountdown = time.time()
                        
                        # Estimate remaining time
                        if stepped_frames != self.counter:
                            self.blender_data["est_render_job"] = str(self.RENDER_CURRENT_FRAME * (stepped_frames - self.counter))[:-4]
                        else:
                            self.blender_data["est_render_job"] = str(self.RENDER_CURRENT_FRAME * (stepped_frames - self.counter + 1))[:-4]
                            
                        # Update per-frame render data
                        self.blender_data["frame"] = current_frame
                        self.blender_data["RENDER_CURRENT_FRAME"] = str(self.RENDER_CURRENT_FRAME)[:-4]
                        self.blender_data["frames_left"] = f"{stepped_frames - self.counter}"
                        self.blender_data["frames_rendered"] = self.counter
                        self.blender_data["rendered_frames_percentage"] = round((self.counter / stepped_frames * 100),2)
                        self.blender_data["countdown"] = f"<t:{self.countdown}:R>"
                        self.blender_data["next_frame_countdown"] = f"<t:{self.current_countdown}:R>"
                        
                        if self.is_discord:
                            try:
                                self.send_webhook_non_blocking(frame=True,blender_data=self.blender_data)
                            except Exception as e:
                                print(f"error in re_post when sending discord: {e}")

                    except Exception as e:
                        print(f"Error in render post (render_post) {e}. possibly cause render job is a still image.")
                        print("its a still render job")
                        
                
                
                # Calculate running average frame render time 
                avg = datetime.now() - datetime.now()
                for est in self.average_est_frames:
                    avg += est
                avg /= len(self.average_est_frames)
                frame = scene.frame_current
                
                self.average_time = avg
                self.blender_data["average_time"] = str(self.average_time)[:-4]
                
                if self.is_third_party_webhook and is_first_frame and self.third_party_webhook_first:
                    self.send_third_party_webhook(stage=1)
                elif self.third_party_webhook_every_frame:
                    self.send_third_party_webhook(stage=4)
                
                if self.is_desktop and is_first_frame and self.desktop_first:
                    self.notify_desktop(
                        title="First frame rendered", 
                        message=f"First frame rendered for: {self.blender_data['project_name']} \ntime: {self.blender_data['RENDER_FIRST_FRAME']} \nEst. render job: {self.blender_data['est_render_job']}"
                        )
        except Exception as e:
            print(f"Error in render post logic: {e}")
            print(self.counter)
        
    # check if rendering frame is the first frame in the timeline
    @persistent
    def on_frame_render(self,scene, *args):
        #print("\nOn Frame Render\n")
        # Check if this is the first frame of the animation
        #if self.current_frame == bpy.context.scene.frame_start:
        #    None
        #    # No path is saved yet since the first frame may not be written at this point
        #else:
        #    # Get the file path of the rendered frame
        #    # `self.rendered_frame_path` stores the absolute path of the currently rendered frame.
        #    # This is useful for saving or processing the rendered frame during the render process.
        #    self.rendered_frame_path = bpy.path.abspath(scene.render.frame_path())
        try:
            self.rendered_frame_path = bpy.path.abspath(scene.render.frame_path())
        except Exception:
            self.rendered_frame_path = None
    
    #handle render complete logic
    @persistent
    def complete(self,scene,*args):
        #print("\nRender Complete\n")
        
        # Track total time taken for the entire render
        self.RENDER_TOTAL_TIME = datetime.now() - self.RENDER_START_TIME
        self.blender_data["call_type"] = "complete"
        self.blender_data["total_time_elapsed"] = str(self.RENDER_TOTAL_TIME)[:-4]
        
        # Detect if the render was a still frame (only one frame rendered)
        if self.current_frame == scene.frame_start:
            self.is_animation = False
            self.job_type = "Still"
            self.blender_data["job_type"] = self.job_type
        
        # Prepare image save path
        final_filename = self.tmp_output_name + self.file_extension
        self.blender_data['final_path'] = self.final_path = os.path.join(self.tmp_output_path, final_filename)
        
        # Schedule save if needed
        def delayed_save():
            try:
                src = getattr(self, 'rendered_frame_path', None)
                print(f"Rendered frame path: {src}")
                if src and os.path.isfile(src):
                    os.makedirs(os.path.dirname(self.final_path), exist_ok=True)
                    shutil.copy2(src, self.final_path)
                    print(f"✅ complete frame copied from: {src} -> {self.final_path}")
                    self.send_webhook_non_blocking(finished=True,blender_data=self.blender_data)
                    return None
            except Exception as e:
                print(f"⚠️ Failed to copy first frame: {e}")
            
            image = bpy.data.images.get('Render Result')
            if image and image.has_data:
                try:
                    os.makedirs(os.path.dirname(self.final_path), exist_ok=True)
                    image.save_render(self.final_path)
                    #print(f"✅ Saved image to: {self.final_path}")
                    if self.is_discord:
                        self.send_webhook_non_blocking(finished=True,blender_data=self.blender_data)
                except Exception as e:
                    print(f"❌ Error saving image (complete): {e}")
                    self.blender_data['no_preview'] = self.no_preview = True
            else:
                print("⚠️ Render Result not ready. (complete)")
            return None
            
        if self.is_animation:
            # Update metadata
            self.blender_data["average_time"] = str(self.average_time)[:-4]
            self.blender_data["total_Est_time"] = str(self.RENDER_FIRST_FRAME * (self.total_frames / self.frame_step))[:-4]
            
        if self.discord_preview and self.is_discord:
            bpy.app.timers.register(delayed_save, first_interval=0.2)
        else:
            if self.is_discord:
                self.send_webhook_non_blocking(finished=True,blender_data=self.blender_data)
        
        if self.is_third_party_webhook and self.third_party_webhook_completion:
            self.send_third_party_webhook(stage=2)
            
        if self.is_desktop and self.desktop_completion:
            self.notify_desktop(
                title="Render completed", 
                message=f"Render job completed for: {self.blender_data['project_name']} \nTotal time elapsed: {self.blender_data['total_time_elapsed']}"
                )
        
        # Reset flags
        self.is_animation = False
        
        #print(f"""
        #===== Render Completed =====
        #Blend File Name: {self.blend_filename}
        #Total Render Time: {self.RENDER_TOTAL_TIME}
        #Total Frames: {self.total_frames}
        #First Frame: {scene.frame_start}
        #Average Render Time per Frame: {self.average_time}
        #First Frame Render Time: {self.RENDER_FIRST_FRAME}
        #==========================
        #""")

    #handle render cancel logic
    @persistent
    def cancel(self,scene,*args):
        # Calculate how long the render was running before it was cancelled
        self.RENDER_CANCELLED_TIME = datetime.now() - self.RENDER_START_TIME
        
        # Capture the current frame at cancellation
        cancel_frame = self.current_frame
        self.blender_data["call_type"] = "cancel"
        self.blender_data["RENDER_CANCELLED_TIME"] = str(self.RENDER_CANCELLED_TIME)[:-4]
        
        # Detect if the render was a still frame (only one frame rendered)
        if self.current_frame == bpy.context.scene.frame_start:
            self.is_animation = False
            self.job_type = "Still"
            self.blender_data["job_type"] = self.job_type
        
        # Prepare image save path 
        final_filename = self.tmp_output_name + self.file_extension
        self.blender_data['final_path'] = self.final_path = os.path.join(self.tmp_output_path, final_filename)
        
        # Schedule image saving if preview is requested
        def delayed_save():
            try:
                src = getattr(self, 'rendered_frame_path', None)
                print(f"Rendered frame path: {src}")
                if src and os.path.isfile(src):
                    os.makedirs(os.path.dirname(self.final_path), exist_ok=True)
                    shutil.copy2(src, self.final_path)
                    print(f"✅ canceled frame copied from: {src} -> {self.final_path}")
                    self.send_webhook_non_blocking(canceled=True,blender_data=self.blender_data)
                    return None
            except Exception as e:
                print(f"⚠️ Failed to copy first frame: {e}")
            
            image = bpy.data.images.get('Render Result')
            if image and image.has_data:
                try:
                    os.makedirs(os.path.dirname(self.final_path), exist_ok=True)
                    image.save_render(self.final_path)
                    #print(f"✅ Saved image to: {self.final_path}")
                    
                    if self.is_discord:
                        self.send_webhook_non_blocking(canceled=True,blender_data=self.blender_data)
                except Exception as e:
                    print(f"❌ Error saving image (cancel): {e}")
                    self.blender_data['no_preview'] = self.no_preview = True
            else:
                print("⚠️ Render Result not ready or missing (cancel).")
            return None
        
        if self.is_animation:
            # Handle animation render cancellation
            self.blender_data["current_frame"] = cancel_frame
            self.blender_data["total_frames_rendered"] = bpy.context.scene.frame_end - cancel_frame
            self.blender_data["frames_still_to_render_range"] = f"{cancel_frame} - {bpy.context.scene.frame_end}"
            self.blender_data["frames_still_to_render"] = f"{round((bpy.context.scene.frame_end - self.current_frame) / self.frame_step)}"
            
        if self.discord_preview and self.is_discord:
            bpy.app.timers.register(delayed_save, first_interval=0.2)
        elif self.is_discord:
            self.send_webhook_non_blocking(canceled=True,blender_data=self.blender_data)
            
        if self.is_third_party_webhook and self.third_party_webhook_cancel:
            self.send_third_party_webhook(stage=3)
            
        if self.is_desktop and self.desktop_cancel:
            self.notify_desktop(
                title="Render canceled", 
                message=f"Render job canceled for: {self.blender_data['project_name']} \nRender canceled after: {self.RENDER_CANCELLED_TIME}"
                )

    # Send JSON payload via third-party webhook to a server (e.g., Flask, Home Assistant, etc.)
    @persistent
    def send_third_party_webhook(self,stage = 0,init=False, isfirstframe=False, finished=False, canceled=False):
        # Use the preconfigured self.third_party_webhook_url
        step_frame = ""
        if self.frame_step > 1:
            step_frame = f"\nFrame Step: {self.blender_data['frame_step']}"
        else:
            step_frame = ""

        
        print(self.is_third_party_simple_render_data)
        if self.is_simple_third_party_webhook:
            match stage:
                case 0: # start
                    payload = self.third_party_on_start
                    
                    if self.is_third_party_simple_render_data and self.job_type == "Animation":
                        payload += f"\nProject: {self.blender_data['project_name']}\nJob Type: {self.blender_data['job_type']}\nTotal Frames ({self.blender_data['frame_range']}): {self.blender_data['total_frames_stepped']}{step_frame}"
                    elif self.is_third_party_simple_render_data:
                        payload += f"\nProject: {self.blender_data['project_name']}\nJob Type: {self.blender_data['job_type']}\nFrame: {self.blender_data['frame']}"""
                case 1: # first frame
                    payload = self.third_party_on_first_frame
                    
                    if self.is_third_party_simple_render_data and self.job_type == "Animation":
                        payload += f"\nProject: {self.blender_data['project_name']}\nJob Type: {self.blender_data['job_type']}\nTotal Frames ({self.blender_data['frame_range']}): {self.blender_data['total_frames_stepped']}{step_frame}\nFirst Frame Time: {self.blender_data['RENDER_FIRST_FRAME']}\nEst. Render Time: {self.blender_data['est_render_job']}"
                case 2: # complete
                    payload = self.third_party_on_completion
                    
                    if self.is_third_party_simple_render_data and self.job_type == "Animation":
                        payload += f"\nProject: {self.blender_data['project_name']}\nJob Type: {self.blender_data['job_type']}\nTotal Frames ({self.blender_data['frame_range']}): {self.blender_data['total_frames_stepped']}{step_frame}\nFirst Frame Time: {self.blender_data['RENDER_FIRST_FRAME']}\nRender Time: {self.blender_data['total_time_elapsed']}\nEst. Render Time: {self.blender_data['total_Est_time']}"
                    elif self.is_third_party_simple_render_data:
                        payload += f"\nProject: {self.blender_data['project_name']}\nJob Type: {self.blender_data['job_type']}\nFrame: {self.blender_data['frame']}\nRender Time: {self.blender_data['total_time_elapsed']}"
                case 3: # cancel
                    payload = self.third_party_on_cancel
                    
                    if self.is_third_party_simple_render_data and self.job_type == "Animation":
                        payload += f"\nProject: {self.blender_data['project_name']}\nJob Type: {self.blender_data['job_type']}\nTotal Frames ({self.blender_data['frame_range']}): {self.blender_data['total_frames_stepped']}{step_frame}\nFirst Frame Time: {self.blender_data['RENDER_FIRST_FRAME']}\nCancelled Frame: {self.blender_data['frame']}\nRender Time (cancelled): {self.blender_data['RENDER_CANCELLED_TIME']}"
                    elif self.is_third_party_simple_render_data:
                        payload += f"\nProject: {self.blender_data['project_name']}\nJob Type: {self.blender_data['job_type']}\nFrame: {self.blender_data['frame']}\nRender Time (cancelled): {self.blender_data['RENDER_CANCELLED_TIME']}"
                case 4: # every frame
                    payload = self.third_party_on_every
                    
                    if self.is_third_party_simple_render_data and self.job_type == "Animation":
                        payload += f"\nProject: {self.blender_data['project_name']}\nJob Type: {self.blender_data['job_type']}\nTotal Frames ({self.blender_data['frame_range']}): {self.blender_data['total_frames_stepped']}{step_frame}\nFirst Frame Time: {self.blender_data['RENDER_FIRST_FRAME']}\nEst. Render Time: {self.blender_data['est_render_job']}"
                
            print(payload)
        else:
            blender_data = self.blender_data
            blender_data.pop('discord_webhook_url', None)
            blender_data.pop('discord_webhook_name', None)
            blender_data.pop('discord_preview', None)
            payload = blender_data
            print(payload)
        import logging

        # Configure logging
        logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(__name__)

        try:
            try:
                response = requests.post(self.third_party_webhook_url, json=payload, timeout=10)
                response.raise_for_status()
            except requests.exceptions.Timeout:
                logger.error("Third-party webhook request timed out.")
            except requests.exceptions.ConnectionError:
                logger.error("Failed to connect to the third-party webhook URL.")
            except requests.exceptions.RequestException as e:
                logger.error(f"An error occurred while sending the third-party webhook: {e}")
            
            if response.status_code == 200:
                logger.info('Third-party webhook sent successfully!')
            else:
                logger.error(f'Failed to send third-party webhook. Status code: {response.status_code}')
                logger.error(response.text)
        except Exception as e:
            logger.exception("Exception while sending third-party webhook.")
    
    @persistent
    def notify_desktop(self, title, message):
        if not title or not message:
            print("⚠️ Title or message is missing for desktop notification.")
            return
        #print("\n Notifying via desktop \n")
        desktop_notify = Notify()
        desktop_notify.title = title
        desktop_notify.message = message
        desktop_notify.application_name = "Blender Render Notifier"
        
        addon_dir = os.path.dirname(__file__)
        icon_path = os.path.join(addon_dir, "resources", "images", "blender_logo.png")
        if os.path.exists(icon_path):
            desktop_notify.icon = icon_path
        else:
            print(f"⚠️ Icon file not found: {icon_path}")
        
        # Optionally play a custom sound if enabled
        if self.is_custom_sound:
            if os.path.isfile(self.desktop_sound_path):
                desktop_notify.audio = self.desktop_sound_path
            else:
                print(f"⚠️ Custom sound file not found or inaccessible: {self.desktop_sound_path}")
        
        try:
            desktop_notify.send()
        except Exception as e:
            print(f"⚠️ Failed to send desktop notification: {e}")

notifier_instance = RenderNotifier()

# List of classes to register
classes = [
    Render_Notifications_Properties, 
    RENDER_PT_Notifications,
    RENDER_PT_Desktop_Notifications,
    RENDER_PT_Discord_Notifications,
    RENDER_PT_Webhook_Notifications,
    RenderNotificationsPreferences,
    RENDER_PT_Simplified_Webhook_Notifications
]

# Register all components and event handlers
def register():
    # Register UI and data classes
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.render_panel_props = bpy.props.PointerProperty(type=Render_Notifications_Properties)
 
    bpy.app.handlers.render_init.append(notifier_instance.render_init)         # Called when render starts
    bpy.app.handlers.render_post.append(notifier_instance.render_post)         # Called after each frame is rendered
    bpy.app.handlers.render_pre.append(notifier_instance.render_pre)           # Called just before rendering starts
    bpy.app.handlers.render_complete.append(notifier_instance.complete)        # Called when render finishes   
    bpy.app.handlers.render_cancel.append(notifier_instance.cancel)            # Called if render is cancelled
    bpy.app.handlers.render_write.append(notifier_instance.on_frame_render)    # Called when a frame is written to disk
        
# Unregister all components and handlers
def unregister():
    # Unregister in reverse order
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    if hasattr(bpy.types.Scene, "render_panel_props"):
        del bpy.types.Scene.render_panel_props

    if notifier_instance:
        # Safely remove handlers
        for handler_list, func in [
            (bpy.app.handlers.render_init, notifier_instance.render_init),
            (bpy.app.handlers.render_post, notifier_instance.render_post),
            (bpy.app.handlers.render_pre, notifier_instance.render_pre),
            (bpy.app.handlers.render_complete, notifier_instance.complete),
            (bpy.app.handlers.render_cancel, notifier_instance.cancel),
            (bpy.app.handlers.render_write, notifier_instance.on_frame_render),
        ]:
            try:
                handler_list.remove(func)
            except ValueError:
                pass  # Already removed or never registered

# Blender add-ons are registered and unregistered using Blender's add-on system.
# Run registration when script is executed directly
#if __name__ == "__main__":
#    register()