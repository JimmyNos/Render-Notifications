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
import requests, socket
import asyncio

from datetime import datetime

import discord
import aiohttp
from notifypy import Notify as NotifyClass
from discord import Webhook as DiscordWebhookClass, Embed as DiscordEmbedClass
Notify = NotifyClass
DiscordWebhook = DiscordWebhookClass
DiscordEmbed = DiscordEmbedClass

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
        description="Name of discotrd bot that will send the notifications. Note: will use the name set in the discord channel webhook settings if this is left empty."
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
    
    ## Webhook ##
    webhook_url: StringProperty( #type: ignore
        name="webhook url",
        description="Webhook url to send notifications to."
    )
    
    # Drawing UI for addon preferences
    def draw(self, context):
        layout = self.layout
        layout.label(text="Setup notifications")
        
        ## Desktop ##
        desktop_box = layout.box()
        row = desktop_box.row()
        desktop_box.label(text="Desktop notifications")
        row = desktop_box.row()
        row.label(text="Custom Sound:")
        row.prop(self, "custom_sound", text="",placeholder="cutom_sound.wav")
        row = desktop_box.row()
        row.label(text="Sound path:")
        row.prop(self, "desktop_sound_path", text="")
        
        ## Discord ##
        discord_box = layout.box()
        row = discord_box.row()
        discord_box.label(text="Discord notifications")
        row = discord_box.row()
        row.label(text="Discord channel webhook name:")
        row.prop(self, "discord_webhook_name", text="")
        row = discord_box.row()
        row.label(text="Discord channel webhook url:")
        row.prop(self, "discord_webhook_url", text="")
        row = discord_box.row()
        row.label(text="Default temporary save location:")
        row.prop(self, "tmp_output_path", text="")
        
        ## Webhook ##
        webhook_box = layout.box()
        row = webhook_box.row()
        webhook_box.label(text="Webhook notifications")
        row = webhook_box.row()
        row.label(text="Webhook url:")
        row.prop(self, "webhook_url", text="")

# Update function for webhook settings
def update_webhook_every_frame(self, context):
    """Toggle all webhook settings when 'notify on every frame' is toggled"""
    state = self.webhook_every_frame
    self.webhook_start = state
    self.webhook_first = state
    self.webhook_completion = state
    self.webhook_cancel = state

# Define a property group to hold the render notifications properties
class RenderNotificationsProperties(PropertyGroup):
    #desktop nitifications
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
        name="Desktop notify with preview",
        description="Send the first and final frame to discord for an animation job, or a still image when a still render job is complete complete. Note: the default save location for the preview is set in the addon prefrences. if the output extention is openEXR or the size of the frame/still is larger than discord's allowed attachment size (with or without nitro), no preview will be sent.",
        default=False  # Starts unchecked
    ) # type: ignore
    use_custom_preview_path: bpy.props.BoolProperty(
        name="Use cutsom preview path",
        description="Use a custom path for the previewed renders that are sent to discord. Note: the default save location for the preview is set in the addon prefrences and will be used if this is unchecked.",
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
    
    #webhook notifications
    webhook_every_frame: bpy.props.BoolProperty(
        name="Webhook notify on everyframe",
        description="Send webhook notifications on everyframe.",
        default=False,  # Starts unchecked
        update=update_webhook_every_frame
    ) # type: ignore
    webhook_start: bpy.props.BoolProperty(
        name="Webhook notify on start",
        description="Send webhook notifications when the render job starts.",
        default=False  # Starts unchecked
    ) # type: ignore
    
    webhook_first: bpy.props.BoolProperty(
        name="Webhook notify on first",
        description="Send webhook notifications when the first frame has rendered.",
        default=False  # Starts unchecked
    )# type: ignore
    webhook_completion: bpy.props.BoolProperty(
        name="Webhook notify on completion",
        description="Send webhook notifications when the render job is complete.",
        default=False  # Starts unchecked
    )# type: ignore
    webhook_cancel: bpy.props.BoolProperty(
        name="Webhook notify on cancel",
        description="Send webhook notifications when the render job is canceled.",
        default=False  # Starts unchecked
    )# type: ignore
    
    
    # Desktop, Discord and Webhook toggle properties
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
    
    is_webhook: bpy.props.BoolProperty(
        name="webhook notifications",  # This will appear as the checkbox label
        description="Enable webhook notifications.",
        default=False
    )# type: ignore

# create UI elaments for addon properties in the render properties tab
class RenderNotificationsRenderPanel(Panel):
    """Creates a notifications panel in the render properties tab"""
    bl_label = "Notifications"
    bl_idname = "RENDER_PT_Notifications"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    bl_parent_id = "RENDER_PT_context"

    # Drawing addon UI in the render properties panel
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.render_panel_props  # Access our custom property
        
        # nitification properties for each notification type
        desktop_box = layout.box()
        row = desktop_box.row(align=True)
        row.prop(props, "is_desktop", text="")  # Checkbox (no extra text)
        row.prop(props, "is_desktop", text="Desktop Notifications", emboss=False, toggle=True,icon='WORLD_DATA')  # Label with dropdown effect
        
        discord_box = layout.box()
        row = discord_box.row(align=True)
        row.prop(props, "is_discord", text="")  # Checkbox (no extra text)
        row.prop(props, "is_discord", text="Discord Notifications", emboss=False, toggle=True,icon='WORLD_DATA')  # Label with dropdown effect
        
        webhook_box = layout.box()
        row = webhook_box.row(align=True)
        row.prop(props, "is_webhook", text="")  # Checkbox (no extra text)
        row.prop(props, "is_webhook", text="Webhook Notifications", emboss=False, toggle=True,icon='WORLD_DATA')  # Label with dropdown effect
        
        # If checkbox is enabled, show additional settings for each notification type
        if props.is_desktop:
            desktop_col = desktop_box.column()
            desktop_col.label(text="Configure Notifications:")
            desktop_col.prop(props, "desktop_start", text="notify on start")
            desktop_col.prop(props, "desktop_first", text="notify on first")
            desktop_col.prop(props, "desktop_completion", text="notify on completion")
            desktop_col.prop(props, "desktop_cancel", text="notify on cancel")
            
        if props.is_discord:
            discord_col = discord_box.column()
            discord_col.label(text="Configure Notifications:")
            discord_col.prop(props, "discord_preview", text="Send previews")
            discord_col.prop(props, "use_custom_preview_path", text="Use custom preview path")
            discord_col.prop(props, "discord_preview_path", text="Previews save location") 
        
        if props.is_webhook:
            webhook_col = webhook_box.column()
            webhook_col.label(text="Configure Notifications:")
            webhook_col.prop(props, "webhook_every_frame", text="notify on everyframe")
            webhook_col.prop(props, "webhook_start", text="notify on start")
            webhook_col.prop(props, "webhook_first", text="notify on first")
            webhook_col.prop(props, "webhook_completion", text="notify on completion")
            webhook_col.prop(props, "webhook_cancel", text="notify on cancel")


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
        
        self.file = None
        self.no_preview = False
        self.rendered_frame_path = ""
        self.file_extension = ".png"
        
        self.discord_preview = False
        self.desktop_cancel = False
        self.webhook_cancel = False
        self.webhook_every_frame = False
        self.is_discord = False
        self.is_webhook = False
        self.is_desktop = False
        self.tmp_output_path = ""
        self.final_path = ""
        self.first_rendered_frame_path = ""
        self.final_first_path = ""
        self.tmp_output_name = ""
        self.tmp_output_name_frist = ""
        
        self.p = None
        
        self.still_embed = DiscordEmbed(type="rich", color=discord.Color.blue())
        self.first_frame_embed = DiscordEmbed(type="rich", color=discord.Color.blue())
        self.animation_embed = DiscordEmbed(type="rich", color=discord.Color.blue())
    
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
        self.total_frames = 0
        self.average_time = 0
        self.job_type = ""
        self.blender_data = {}
        self.current_frame = None
        self.counter = 0
        self.precountdown = 0.0
        
        self.tmp_output_name = ""
        self.tmp_output_name_frist = ""

    # handle discord webhook using a separate thread-safe event loop
    def send_webhook_non_blocking(self, init=False, frame=False, finished=False, canceled=False):
        try:
            start_timer = time.time()
            print("Sending data to subprocess:", self.blender_data)
            try:
                s = json.dumps(self.blender_data) + "\n"
                self.p.stdin.write(s)
                print("Written to subprocess stdin:")
                self.p.stdin.flush()
                print("Flushed subprocess stdin.")
            except Exception as e:
                print(f"Error writing to subprocess: {e}")

            print("Data sent to subprocess")
            #print("Data sent to subprocess, waiting for response...")
            ## Read response
            #out_line = self.p.stdout.readline()
            #print("Response received from subprocess:", out_line)
            #print("\n\n")
            ## Check for EOF
            #if not out_line:
            #    print("No response (EOF).")
            #    
            ## process the response
            #try:
            #    parsed = json.loads(out_line.strip())
            #    print("Response:", parsed)
            #except Exception:
            #    print("Error parsing JSON response: (raw)", out_line.strip())
            
            
            try:
                if finished or canceled:
                    # Send exit command
                    self.p.stdin.close()
                    ret = self.p.wait(timeout=5)
                    err = self.p.stderr.read()
                    print("Process finished. returncode=", ret)
                    if err:
                        print("Stderr:", err.strip())
            except Exception as e:
                print(f"Error closing subprocess: {e}")
            print(f"✅ Successfully ran writing subprocess in {time.time() - start_timer} seconds")
        except Exception as e:
            print(f"⚠️ Error occurred while running writing subproccess: {e}")

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
        
        self.blender_data["call_type"] = "render_init"
        self.blender_data["project_name"] = self.blend_filename
        self.blender_data["total_frames"] = self.total_frames
        
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
            discord_proccess = os.path.join(addon_dir, "discord_proccess.py")
            # Use -u for unbuffered output so we can stream
            self.p = subprocess.Popen(
                [sys.executable, "-u", discord_proccess],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            
            #print("Process started.")
            #
            #print("Writing to subprocess...")
            #print("Sending data to subprocess:", self.blender_data)
            #s = json.dumps(self.blender_data) + "\n"
            #self.p.stdin.write(s)
            #self.p.stdin.flush()

            #print("Data sent to subprocess, waiting for response...")
            ## Read response
            #out_line = self.p.stdout.readline()
            #print("Response received from subprocess:", out_line)
            ## Check for EOF
            #if not out_line:
            #    print("No response (EOF).")
            #    
            ## process the response
            #try:
            #    parsed = json.loads(out_line.strip())
            #    print("Response:", parsed)
            #except Exception:
            #    print("Error parsing JSON response: (raw)", out_line.strip())
            #    discord_preview
            ## Send exit command
            #self.p.stdin.close()
            #ret = self.p.wait(timeout=5)
            #err = self.p.stderr.read()
            #print("Process finished. returncode=", ret)
            #if err:
            #    print("Stderr:", err.strip())
        
        ## Webhook ##
        self.webhook_url = bpy.context.preferences.addons[addon_name].preferences.webhook_url
        self.is_webhook = bpy.context.scene.render_panel_props.is_webhook
        self.webhook_every_frame = bpy.context.scene.render_panel_props.webhook_every_frame
        self.webhook_start = bpy.context.scene.render_panel_props.webhook_start
        self.webhook_first = bpy.context.scene.render_panel_props.webhook_first
        self.webhook_completion = bpy.context.scene.render_panel_props.webhook_completion
        self.webhook_cancel = bpy.context.scene.render_panel_props.webhook_cancel
        
    # Handle render pre logic render_start_countdown
    @persistent
    def render_pre(self,scene,*args):
        #print("\nPre Render\n")
        self.current_frame = bpy.context.scene.frame_current
        self.blender_data["frame"] = bpy.context.scene.frame_current
        self.blender_data["isfirst_frame"] = self.isfirst_frame = self.current_frame == bpy.context.scene.frame_start
        # check if the render job is an animation or a still image 
        if self.current_frame == bpy.context.scene.frame_start:
            self.is_animation = True
            self.job_type = "Animation"  
            self.blender_data["job_type"] = self.job_type
            self.blender_data["frame"] = self.current_frame
            self.blender_data["frame_range"] = f"{bpy.context.scene.frame_start} - {bpy.context.scene.frame_end}"
            self.blender_data["Total_frames_to_render"] = self.total_frames
            
            if self.is_discord:
                self.send_webhook_non_blocking(init=True)
                #self.blender_data["discord_webhook_url"] = "cleared" # clear webhook url after init
            
            if self.is_webhook and self.webhook_start:
                self.send_webhook()
              
            if self.is_desktop and self.desktop_start:
                self.notifi_desktop(
                    title="Render started", 
                    message="Render job started for: " + self.blender_data["project_name"]
                    )
        
        # if the current frame is not the first frame, it is a still image render job
        elif self.current_frame != bpy.context.scene.frame_start and self.is_animation == False:
            #is_animation = False
            self.job_type = "Still"
            self.blender_data["job_type"] = self.job_type
            self.blender_data["frame"] = self.current_frame
            if self.is_discord:
                self.send_webhook_non_blocking(init=True)
            
            if self.is_webhook and self.webhook_start:
                self.send_webhook()
                
            if self.is_desktop and self.desktop_start:
                self.notifi_desktop(
                    title="Render started", 
                    message="Render job started for: " + self.blender_data["project_name"]
                    )
        #print(f"Render job type: {self.job_type}")
        
    # Handle render post logic
    @persistent   
    def render_post(self,scene,*args):
        #print("\nPost Render\n")
        
        # Track call type for logging or webhook purposes
        self.blender_data["call_type"] = "render_post"
        self.current_frame = scene.frame_current
        first_frame = False
        
        try:
            if self.is_animation:
                # Check if this is the first frame of the animation
                first_frame = self.current_frame == scene.frame_start
                
                if first_frame:
                    self.RENDER_FIRST_FRAME = datetime.now() - self.RENDER_START_TIME
                    
                    # Estimate average time per frame and total job duration
                    self.precountdown = time.time() - self.render_start_countdown
                    self.countdown = int(time.time() + self.precountdown * (self.total_frames - self.counter))
                    self.current_countdown = int(time.time() + self.precountdown)
                    self.precountdown = time.time()
                    
                    self.average_est_frames.append(self.RENDER_FIRST_FRAME)
                    self.RENDER_PRE_TIME = datetime.now()
                    self.counter += 1
                    
                    # Populate render info for sending to Discord or display
                    self.blender_data["frame"] = scene.frame_start
                    self.blender_data["RENDER_FIRST_FRAME"] = str(self.RENDER_FIRST_FRAME)[:-4]
                    self.blender_data["est_render_job"] = str(self.RENDER_FIRST_FRAME * (self.total_frames - self.counter))[:-4]
                    self.blender_data["frames_left"] = f"{self.total_frames - self.counter}"
                    self.blender_data["frames_rendered"] = self.counter
                    self.blender_data["rendered_frames_percentage"] = round((self.counter / self.total_frames * 100),2)
                    self.blender_data["countdown"] = f"<t:{self.countdown}:R>"
                    self.blender_data["next_frame_countdown"] = f"<t:{self.current_countdown}:R>"
                    
                    if self.discord_preview and self.is_discord: # save first frame if discord preview is enabled
                        first_filename = self.tmp_output_name_frist + self.file_extension
                        self.blender_data['final_first_path'] = self.final_first_path = os.path.join(self.first_rendered_frame_path, first_filename)
                    
                        
                        def delayed_first_frame_save():
                            # Prefer copying the file that Blender wrote to disk (most reliable).
                            try:
                                src = getattr(self, 'rendered_frame_path', None)
                                print(f"Rendered frame path: {src}")
                                if src and os.path.isfile(src):
                                    os.makedirs(os.path.dirname(self.final_first_path), exist_ok=True)
                                    shutil.copy2(src, self.final_first_path)
                                    print(f"✅ First frame copied from: {src} -> {self.final_first_path}")
                                    self.send_webhook_non_blocking(frame=True)
                                    return None
                            except Exception as e:
                                print(f"⚠️ Failed to copy first frame: {e}")
                            
                            image = bpy.data.images.get('Render Result')
                            if image and image.has_data:
                                try:
                                    os.makedirs(os.path.dirname(self.final_first_path), exist_ok=True)
                                    image.save_render(self.final_first_path)
                                    print(f"✅ First frame saved to: {self.final_first_path}")
                                    self.send_webhook_non_blocking(frame=True)
                                except Exception as e:
                                    print(f"❌ Failed to save first frame (render_post): {e}")
                                    self.blender_data['no_first_preview'] = self.no_first_preview = True
                                    print(f"⚠️ First frame preview not available. ({self.blender_data['no_first_preview']})")
                                    self.send_webhook_non_blocking(frame=True)
                            else:
                                print("⚠️ Render Result not available for first frame. (render_post)")
                            return None

                        bpy.app.timers.register(delayed_first_frame_save, first_interval=0.2)   
                    elif self.is_discord and not self.discord_preview:
                        try:
                            self.send_webhook_non_blocking(frame=True)
                        except Exception as e:
                            print(f"error in re_post when sending first frame discord: {e}")
                else:
                    try:
                        # Time per frame and ETA calculations
                        self.precountdown = time.time() - self.precountdown
                        self.countdown = int(time.time() + self.precountdown * (self.total_frames - self.counter))
                        self.current_countdown = int(time.time() + self.precountdown)
                        self.counter += 1
                        self.RENDER_CURRENT_FRAME = datetime.now() - self.RENDER_PRE_TIME
                        self.average_est_frames.append(self.RENDER_CURRENT_FRAME) 
                        self.RENDER_PRE_TIME = datetime.now()
                        self.precountdown = time.time()
                        
                        # Estimate remaining time
                        if self.total_frames != self.counter:
                            self.blender_data["est_render_job"] = str(self.RENDER_CURRENT_FRAME * (self.total_frames - self.counter))[:-4]
                        else:
                            self.blender_data["est_render_job"] = str(self.RENDER_CURRENT_FRAME * (self.total_frames - self.counter + 1))[:-4]
                            
                        # Update per-frame render data
                        self.blender_data["frame"] = scene.frame_current
                        self.blender_data["RENDER_CURRENT_FRAME"] = str(self.RENDER_CURRENT_FRAME)[:-4]
                        self.blender_data["frames_left"] = f"{self.total_frames - self.counter}"
                        self.blender_data["frames_rendered"] = self.counter
                        self.blender_data["rendered_frames_percentage"] = round((self.counter / self.total_frames * 100),2)
                        self.blender_data["countdown"] = f"<t:{self.countdown}:R>"
                        self.blender_data["next_frame_countdown"] = f"<t:{self.current_countdown}:R>"
                        
                        if self.is_discord:
                            try:
                                self.send_webhook_non_blocking(frame=True)
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
                
                if self.is_webhook and first_frame and self.webhook_first:
                    self.send_webhook()
                elif self.webhook_every_frame:
                    self.send_webhook()
                
                if self.is_desktop and first_frame and self.desktop_first:
                    self.notifi_desktop(
                        title="First frame rendered", 
                        message=f"First frame rendered for: {self.blender_data['project_name']} \ntime: {self.blender_data['RENDER_FIRST_FRAME']} \nEst. render job: {self.blender_data['est_render_job']}"
                        )
        except Exception as e:
            print(f"Error in render post logic: {e}")
            print(self.counter)
        #print("Render Post Logic Completed")
        
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
        
        #print(f"discord_preview: {self.discord_preview}")
        
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
                    self.send_webhook_non_blocking(frame=True)
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
                        self.send_webhook_non_blocking(finished=True)
                except Exception as e:
                    print(f"❌ Error saving image (complete): {e}")
                    self.blender_data['no_preview'] = self.no_preview = True
            else:
                print("⚠️ Render Result not ready. (complete)")
            return None
            
        if self.is_animation:
            # Update metadata
            self.blender_data["average_time"] = str(self.average_time)[:-4]
            self.blender_data["total_Est_time"] = str(self.RENDER_FIRST_FRAME * self.total_frames)[:-4]
            
        if self.discord_preview and self.is_discord:
            bpy.app.timers.register(delayed_save, first_interval=0.2)
        else:
            if self.is_discord:
                self.send_webhook_non_blocking(finished=True)
        
        if self.is_webhook and self.webhook_completion:
            self.send_webhook()
            
        if self.is_desktop and self.desktop_completion:
            self.notifi_desktop(
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
                    self.send_webhook_non_blocking(frame=True)
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
                        self.send_webhook_non_blocking(canceled=True)
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
            self.blender_data["frames_still_to_render"] = f"{bpy.context.scene.frame_end - self.current_frame}"
            
        if self.discord_preview and self.is_discord:
            bpy.app.timers.register(delayed_save, first_interval=0.2)
        elif self.is_discord:
            self.send_webhook_non_blocking(canceled=True)
            
        if self.is_webhook and self.webhook_cancel:
            self.send_webhook()
            
        if self.is_desktop and self.desktop_cancel:
            self.notifi_desktop(
                title="Render canceled", 
                message=f"Render job canceled for: {self.blender_data['project_name']} \nRender canceled after: {self.RENDER_CANCELLED_TIME}"
                )

    # Send JSON payload via webhook to a server (e.g., Flask, Home Assistant, etc.)
    @persistent
    def send_webhook(self):
        # Use the preconfigured self.webhook_url
        payload = self.blender_data
        import logging

        # Configure logging
        logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(__name__)

        try:
            try:
                response = requests.post(self.webhook_url, json=payload, timeout=10)
                response.raise_for_status()
            except requests.exceptions.Timeout:
                logger.error("Webhook request timed out.")
            except requests.exceptions.ConnectionError:
                logger.error("Failed to connect to the webhook URL.")
            except requests.exceptions.RequestException as e:
                logger.error(f"An error occurred while sending the webhook: {e}")
            
            if response.status_code == 200:
                logger.info('Webhook sent successfully!')
            else:
                logger.error(f'Failed to send webhook. Status code: {response.status_code}')
                logger.error(response.text)
        except Exception as e:
            logger.exception("Exception while sending webhook.")
    
    @persistent
    def notifi_desktop(self, title, message):
        if not title or not message:
            print("⚠️ Title or message is missing for desktop notification.")
            return
        #print("\n Notifing via desktop \n")
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
    RenderNotificationsProperties, 
    RenderNotificationsRenderPanel, 
    RenderNotificationsPreferences
]

# Register all components and event handlers
def register():
    # Register UI and data classes
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.render_panel_props = bpy.props.PointerProperty(type=RenderNotificationsProperties)
 
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