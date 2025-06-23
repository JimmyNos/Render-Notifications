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

bl_info = {
    "name": "Render Notifications",
    "author": "Michael Mosako (JimmyNoStar)",
    "version": (1, 0, 0),
    "blender": (4, 3, 2),
    "location": "Render properties",
    "description": "Sends webhooks, discord and desktop notifications to notify you when your render starts, finishes, or is canceled.",
    "wiki_url": "https://github.com/JimmyNos/Render-Notifications",
    "category": "Render"
}

import time
import bpy

from bpy.types import Operator, AddonPreferences,PropertyGroup,Panel
from bpy.props import StringProperty, IntProperty, BoolProperty
from bpy.app.handlers import persistent

import sys, subprocess, os, site, platform
import json
import requests, socket
import asyncio

from datetime import datetime
import threading

# This class is used to get the python executable path based on the OS
class Get_sys_path():
    @staticmethod
    def isWindows():
        return os.name == 'nt'

    @staticmethod
    def isMacOS():
        return os.name == 'posix' and platform.system() == "Darwin"

    @staticmethod
    def isLinux():
        return os.name == 'posix' and platform.system() == "Linux"

    @staticmethod
    def python_exec():
        
        if Get_sys_path.isWindows():
            return os.path.join(sys.prefix, 'bin', 'python.exe')
        elif Get_sys_path.isMacOS():
            try:
                # 2.92 and older
                path = bpy.app.binary_path_python
            except AttributeError:
                # 2.93 and later
                path = sys.executable
            return os.path.abspath(path)
        elif Get_sys_path.isLinux():
            return os.path.join(sys.prefix, 'bin', 'python3.11')
        else:
            print("sorry, still not implemented for ", os.name, " - ", platform.system())
            return sys.executable  # Safe fallback

def install_package(pkg_name):
    user_site = site.getusersitepackages()
    
    # Check if user site-packages path is in sys.path
    if user_site not in sys.path:
        sys.path.append(user_site)
        print(f"✅ Added user site-packages path: {user_site}")
    else:
        print(f"✅ Already in user site-packages path: {user_site}")
        
    get_sys_path = Get_sys_path()
    python_exe = get_sys_path.python_exec()
    
    try:
        print("installing missing libaries")
        subprocess.run([python_exe, '-m', 'ensurepip'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        subprocess.run([python_exe, '-m', 'pip', 'install', '--upgrade', 'pip'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        
        subprocess.run([python_exe, "-m", "pip", "install", pkg_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        return True
    except Exception as e:
        print(f"Install failed: {e}")
        return False

# Will try to import the required packages, if not installed, will set them to None
class RenderNotifications_OT_InstallDeps(bpy.types.Operator):
    bl_idname = "rendernotify.install_deps"
    bl_label = "Install notify-py, discord.py and aiohttp"
    addon_name = __package__

    def execute(self, context):
        success_notify = install_package("notify-py")
        success_discord = install_package("discord")
        success_aiohttp = install_package("aiohttp")

        if success_discord and success_aiohttp and success_notify:
            #self.report({'INFO'}, "Dependencies installed successfully.")
            bpy.context.preferences.addons[__name__].preferences.is_installed = True
            bpy.context.preferences.addons[__name__].preferences.installed_msg = "Libraries are now installed. Warning: please reload the addon!"
            self.report({'INFO'}, "Dependencies installed. Please disable and re-enable the addon.")

        else:
            self.report({'ERROR'}, "Failed to install one or more packages.")
        return {'FINISHED'}

# Define the addon preferences class
class RenderNotificationsPreferences(AddonPreferences):
    bl_idname = __name__
    
    #properties for installing libraries
    is_installed: BoolProperty( # type: ignore
        name="Is Installed",
        description="Indicates if the addon is installed correctly",
        default=False
    ) 
    installed_msg: StringProperty( #type: ignore
        name="libraries installed message",
        description="Message showen after libraries have been installed"
    ) 
    
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
        
        install_box = layout.box()
        row = install_box.row(align=False,heading="test")
        if None in (Notify, discord, aiohttp): # If libraries are missing, then extra labels and a button to intall then will appear 
            install_col = install_box.column()
            install_col.label(text="Missing libraries: notifypy, discord.py, aiohttp")
            install_col.label(text="Please install them to use the plugin!")
            install_col.operator("rendernotify.install_deps", text="Install missing libraries",icon="CANCEL")
            if self.is_installed:
                row = install_box.row()
                row.label(text=self.installed_msg)
                row.label(icon="CHECKMARK")
        else:
            #print(f"is_installed: {self.is_installed}")      
            row.label(text="All libraries are installed.")
            row.label(icon="CHECKMARK")
            self.is_installed = True
        
        if self.is_installed:
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
        
        
        self.still_embed = DiscordEmbed(type="rich", color=discord.Color.blue())
        self.first_frame_embed = DiscordEmbed(type="rich", color=discord.Color.blue())
        self.animation_embed = DiscordEmbed(type="rich", color=discord.Color.blue())

        self.end = False
        # Start an asyncio event loop in a separate thread
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.run_async_loop, daemon=True).start()
    
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
    
    # run the asyncio event loop in a separate thread
    # This method initializes and runs an asyncio event loop in a separate thread.
    # It is primarily used for handling Discord webhook operations asynchronously.
    # The `self.end` flag is checked to determine if the loop should be stopped.
    # When `self.end` is set to True, the loop is stopped gracefully to avoid resource leaks.
    def run_async_loop(self):
        """
        Initializes and runs an asyncio event loop in a separate thread.

        Purpose:
        - This method is used to handle asynchronous operations, such as sending Discord webhook messages,
          without blocking the main thread of the application.

        Interaction with `self.end`:
        - The `self.end` flag is a boolean that signals when the event loop should stop.
        - If `self.end` is set to True, the method stops the event loop gracefully to ensure proper cleanup.

        Usage:
        - This method is called during the initialization of the RenderNotifier class to start the event loop.
        - It allows asynchronous tasks to be scheduled and executed in a thread-safe manner.

        Note:
        - The event loop runs indefinitely unless explicitly stopped by setting `self.end` to True.
        """
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        if self.end:
            self.loop.stop()
    
    # Send a new discord message or edit embeded message
    async def send_or_update_embed(self, init=False, frame=False, finished=False, canceled=False):
        """Send a new webhook message or update the existing one."""
        if init:
            if self.blender_data['job_type'] == "Animation": 
                self.em_init(True)
            else: 
                self.em_init(False)  
            
        elif frame:
            if self.blender_data['job_type'] == "Animation": 
                self.em_post(True)
            else: 
                self.em_post(False)
                    
        elif finished:
            if self.blender_data['job_type'] == "Animation": 
                self.em_complete(True)
            else: 
                self.em_complete(False)
                
        elif canceled:
            if self.blender_data['job_type'] == "Animation": 
                self.em_cancel(True)
            else: 
                self.em_cancel(False)
                
        
        async def edit_still(has_attch = False):
            if finished:
                if has_attch:
                    await webhook.edit_message(self.message_id, embed=self.still_embed,attachments=[self.file])
                else:
                    await webhook.edit_message(self.message_id, embed=self.still_embed)
                    
                await self.send_on_complete(full_hook, webhook)
            elif canceled:
                if has_attch:
                    await webhook.edit_message(self.message_id, embed=self.still_embed,attachments=[self.file])
                else:
                    await webhook.edit_message(self.message_id, embed=self.still_embed)
                    
                await self.send_on_cancel(full_hook, webhook)
            else:
                await webhook.edit_message(self.message_id, embed=self.still_embed)
        
        async def edit_animation(has_attch = False):
            if finished:
                if has_attch:
                    await webhook.edit_message(self.message_id, embed=self.animation_embed,attachments=[self.file,self.thumbfile])
                else:
                    await webhook.edit_message(self.message_id, embed=self.animation_embed)
                
                await self.send_on_complete(full_hook, webhook)
            elif canceled:
                if has_attch:
                    await webhook.edit_message(self.message_id, embed=self.animation_embed,attachments=[self.file,self.thumbfile])
                else:
                    await webhook.edit_message(self.message_id, embed=self.animation_embed)
                
                await self.send_on_cancel(full_hook, webhook)
            elif self.blender_data["frames_rendered"] == 1:
                if has_attch:
                    await webhook.edit_message(self.message_id, embed=self.animation_embed,attachments=[self.thumbfile])
                else:
                    await webhook.edit_message(self.message_id, embed=self.animation_embed)
            else:
                await webhook.edit_message(self.message_id, embed=self.animation_embed)
        
        # Hanlde sending this discord webhook message
        async with aiohttp.ClientSession() as session:
            webhook = DiscordWebhook.from_url(self.discord_webhook_url, session=session)
            if self.message_id:
                # If message_id is set, edit the existing message
                try:
                    full_hook = await webhook.fetch()
                    if self.blender_data['job_type'] == "Animation": 
                        # If the preview is enabled, send the embed with the preview images
                        if self.discord_preview:
                            try:
                                await edit_animation(True)
                            except Exception as e:
                                # If the embed is too large or an error is cought, try to send it without the image
                                print(f"Error occurred while embedding image in Discord webhook: {e}. This might be due to file size limitations or an invalid file path. (possiable fix: try reloading blender)")
                                self.animation_embed.description+= "\n Render too large for preview or failed to save."
                                await edit_animation()
                        else:
                            await edit_animation()
                    else:
                        # Send still embed if the job is not an animation
                        if self.discord_preview:
                            try:
                                await edit_still(True)
                            except Exception as e:
                                # If the embed is too large or an error is cought, try to send it without the image
                                print(f"Error occurred while embedding image in Discord webhook: {e}. This might be due to file size limitations or an invalid file path. (possiable fix: try reloading blender)")
                                self.still_embed.description+= "\n Render too large for preview or failed to save."
                                await edit_still()
                        else:
                            await edit_still()
                        
                    
                    # If the job is finished or canceled, clear the message_id                  
                    if canceled or finished:
                        #self.animation_embed.clear_fields()
                        #self.still_embed.clear_fields()
                        self.message_id = None
                        
                except aiohttp.ClientError as client_error:
                    print(f"⚠️ Client error occurred while updating message: {client_error}")
                except discord.errors.HTTPException as http_error:
                    print(f"⚠️ HTTP error occurred while updating message: {http_error}")
                except Exception as e:
                    print(f"⚠️ Unexpected error occurred while updating message: {e}")
                    
            else: # if message_id is not set, send a new message
                if self.blender_data['job_type'] == "Animation": 
                    msg = await webhook.send(embed=self.first_frame_embed, username=self.discord_webhook_name, wait=True)
                    self.message_id = msg.id
                    
                else:
                    if self.isfirst_frame:
                        msg = await webhook.send(embed=self.first_frame_embed, username=self.discord_webhook_name, wait=True)
                    else:
                        msg = await webhook.send(embed=self.still_embed, username=self.discord_webhook_name, wait=True)
                    self.message_id = msg.id
    
    # Send a discord message when the render job is complete         
    async def send_on_complete(self, full_hook=None, webhook=None):
        #print(f"full_hook.guild_id: {full_hook.guild_id}, full_hook.channel_id: {full_hook.channel_id}, self.message_id: {self.message_id}")
        message_link = f"https://discord.com/channels/{full_hook.guild_id}/{full_hook.channel_id}/{self.message_id}"
        reply_content = f"{message_link}" # link to main message
        self.complete_embed.description += f"\n## {reply_content}"
        await webhook.send(username=self.discord_webhook_name, embed=self.complete_embed)
        #print("reply sent")
    
    # Send a discord message when the render job is canceled
    async def send_on_cancel(self, full_hook=None, webhook=None):
        #print(f"full_hook.guild_id: {full_hook.guild_id}, full_hook.channel_id: {full_hook.channel_id}, self.message_id: {self.message_id}")
        message_link = f"https://discord.com/channels/{full_hook.guild_id}/{full_hook.channel_id}/{self.message_id}"
        reply_content = f"{message_link}" # link to main message
        self.cancel_embed.description += f"\n## {reply_content}"
        await webhook.send(username=self.discord_webhook_name, embed=self.cancel_embed)
        #print("reply sent")
    
    # handle discord webhook using a separate thread-safe event loop
    def send_webhook_non_blocking(self, init=False, frame=False, finished=False, canceled=False):
        """Schedule webhook execution using a separate thread-safe event loop."""
        try:
            
            future = asyncio.run_coroutine_threadsafe(
                self.send_or_update_embed(init, frame, finished, canceled),
                self.loop
            )
            future.result()  # Ensure the coroutine executes correctly
            #future.add_done_callback(lambda f: print(f"Coroutine completed with result: {f.result()}"))
        except Exception as e:
            print(f"⚠️ Error occurred while running coroutine thread-safe: {e} {self.blender_data['frames_rendered']}")

    # Load data into embeds
    def em_init(self,isAnimation):
        # create the embed messages
        self.animation_embed = DiscordEmbed(title=self.blender_data['project_name'], 
                                     description=f"Starting render job.. <t:{int(self.render_start_countdown)}:R>", 
                                     colour=discord.Colour.blue())
        
        self.still_embed = DiscordEmbed(title=self.blender_data['project_name'], 
                                 description=f"Starting render job.. <t:{int(self.render_start_countdown)}:R>", 
                                 colour=discord.Colour.gold())
        self.first_frame_embed = DiscordEmbed(title=self.blender_data['project_name'], 
                                       description=f"Starting render job.. <t:{int(self.render_start_countdown)}:R>", 
                                       colour=discord.Colour.blue())
        
        self.complete_embed = DiscordEmbed(title="*Render completed :white_check_mark:*", 
                               description=f"Render job for {self.blender_data['project_name']} completed successfully!", 
                               colour=discord.Colour.light_embed(),
                               timestamp=discord.utils.utcnow())
        
        self.cancel_embed = DiscordEmbed(title="*Render canceled :x:*", 
                               description=f"Render job for {self.blender_data['project_name']} was canceled!", 
                               colour=discord.Colour.light_embed(),
                               timestamp=discord.utils.utcnow())
        
        #print("Starting")
        
        # set the embed fields with the data genarated from blender   
        if isAnimation: 
            self.animation_embed.add_field(name="Job type", value=self.blender_data['job_type'], inline=False)
            self.animation_embed.add_field(name="Total frames", value=self.blender_data['total_frames'], inline=True)
            self.animation_embed.add_field(name="Frame Range", value=self.blender_data['frame_range'], inline=True)
            self.animation_embed.add_field(name="Frame", value="...", inline=True)
            self.animation_embed.add_field(name="frames rendered", value="...", inline=True)
            self.animation_embed.add_field(name="Frame time", value="...", inline=True)
            self.animation_embed.add_field(name="Est. next frame", value="...", inline=True)
            self.animation_embed.add_field(name="Avarage per frame", value="...", inline=False)
            self.animation_embed.add_field(name="Est. render job", value="...", inline=True)
            self.animation_embed.add_field(name="Total est. time", value="...", inline=True)
            self.animation_embed.add_field(name="Total time elapsed", value="...", inline=True)
            self.animation_embed.set_footer(text="*(^◕.◕^)*")
            
            self.first_frame_embed.add_field(name="Job type", value=self.blender_data['job_type'], inline=False)
            self.first_frame_embed.add_field(name="Total frames", value=self.blender_data['total_frames'], inline=True)
            self.first_frame_embed.add_field(name="Frame Range", value=self.blender_data['frame_range'], inline=True)
            self.first_frame_embed.add_field(name="Frame", value=self.blender_data['frame'], inline=True)
            self.first_frame_embed.add_field(name="Total est. time", value="...", inline=True)
            self.first_frame_embed.add_field(name="Total time elapsed", value="...", inline=False)
            self.first_frame_embed.set_footer(text="*(^◕.◕^)*")
            
            # set the still embed fields with the data genarated from blender is its a the first frame of the timeline
            if self.isfirst_frame:
                self.still_embed.add_field(name="Job type", value=self.blender_data['job_type'], inline=True)
                self.still_embed.add_field(name="Frame", value=self.blender_data['frame'], inline=True)
                self.still_embed.add_field(name="Total time elapsed", value="...", inline=False)
                self.still_embed.set_footer(text="(。>︿<)_θ")
        else: 
            self.still_embed.add_field(name="Job type", value=self.blender_data['job_type'], inline=True)
            self.still_embed.add_field(name="Frame", value=self.blender_data['frame'], inline=True)
            self.still_embed.add_field(name="Total time elapsed", value="...", inline=False)
            self.still_embed.set_footer(text="(。>︿<)_θ")
    
    # Load new data into embeds every time a frame is rendered
    def em_post(self,isAnimation):
        #print(f"Updating embed with new data {isAnimation}, Frames rendered: {self.blender_data['frames_rendered']}")
        if isAnimation: 
            
            self.frames_rendered_feild = "("+str(self.blender_data['frames_rendered'])+"/"+str(self.blender_data['total_frames'])+") "+str(self.blender_data['rendered_frames_percentage'])+"%"
            
            #check if it's the first frame
            if self.blender_data["frames_rendered"] == 1:
                #print("First frame rendered")
                if self.discord_preview and self.no_preview == False:
                    try:
                        if os.path.isfile(self.final_first_path):
                            #print("valid file path")
                            self.thumbfile=discord.File(self.final_first_path,filename="first_render.png")
                            thumbattach = "attachment://first_render.png"
                            self.animation_embed.set_thumbnail(url=thumbattach)
                            self.first_frame_embed.set_thumbnail(url=thumbattach)
                        else:
                            print(f"⚠️ File not found: {self.final_first_path}")
                            self.thumbfile = None
                    except Exception as e:
                        print(f"Error occurred while setting thumbnail for first frame in en_post: {e}")
                    
                
                
                self.animation_embed.description += "\nFirst frame rendered"
                self.animation_embed.set_field_at(index=3,name="Frame", value=self.blender_data['frame'], inline=False)
                self.animation_embed.set_field_at(index=4,name="frames rendered", value=self.frames_rendered_feild, inline=True)
                self.animation_embed.set_field_at(index=5,name="Frame time", value=self.blender_data['RENDER_FIRST_FRAME'], inline=True)
                self.animation_embed.set_field_at(index=6,name="Est. next frame", value=self.blender_data['next_frame_countdown'], inline=True)
                self.animation_embed.set_field_at(index=8,name=f"Est. render job {self.blender_data['countdown']}", value=self.blender_data['est_render_job'], inline=False)
                self.animation_embed.colour=discord.Colour.gold()
                
                self.animation_embed.set_footer(text= "(。>︿<)_θ")
            else:
                self.animation_embed.set_field_at(index=3,name="Frame", value=self.blender_data['frame'], inline=False)
                self.animation_embed.set_field_at(index=4,name="frames rendered", value=self.frames_rendered_feild, inline=True)
                self.animation_embed.set_field_at(index=5,name="Frame time", value=self.blender_data['RENDER_CURRENT_FRAME'], inline=True)
                self.animation_embed.set_field_at(index=6,name="Est. next frame", value=self.blender_data['next_frame_countdown'], inline=True)
                self.animation_embed.set_field_at(index=7,name="Avarage per frame", value=f"{self.blender_data['average_time']}", inline=True)
                self.animation_embed.set_field_at(index=8,name=f"Est. render job {self.blender_data['countdown']}", value=self.blender_data['est_render_job'], inline=False)
      
    # Load new data into embeds when the render job is complete  
    def em_complete(self,isAnimation):
        if isAnimation: 
            try:
                if self.discord_preview and self.no_preview == False:
                    try: # try to upload the preview images
                        if os.path.isfile(self.final_path):
                            # set the image as the complete render
                            self.file = discord.File(self.final_path, filename="complete_render.png")
                            attach = "attachment://complete_render.png"
                            self.animation_embed.set_image(url=attach)
                        else:
                            print(f"⚠️ File not found: {self.final_path}")
                            self.file = None
                        
                        if os.path.isfile(self.final_first_path):
                            # set the thumbnail as the first frame
                            self.thumbfile=discord.File(self.final_first_path,filename="first_render.png")
                            thumbattach = "attachment://first_render.png"
                            self.animation_embed.set_thumbnail(url=thumbattach)
                        else:
                            print(f"⚠️ File not found: {self.final_first_path}")
                            self.thumbfile = None
                    except Exception as e:
                        print(f"An error occurred en_com when uploading images: {e}")
                        
                self.animation_embed.description += "\nRender complete"
                self.animation_embed.set_field_at(index=7, name="Avarage per frame", value=self.blender_data['average_time'], inline=True)
                self.animation_embed.set_field_at(index=9, name="Total est. time", value=self.blender_data['total_Est_time'], inline=True)
                self.animation_embed.set_field_at(index=10, name="Total time elapsed", value=self.blender_data['total_time_elapsed'], inline=True)
                self.animation_embed.set_footer(text="( *︾▽︾)")
                
                if self.discord_preview and self.no_preview == False:
                    try:
                        if os.path.isfile(self.final_path):
                            self.file = discord.File(self.final_path, filename="complete_render.png")
                            attach = "attachment://complete_render.png"
                            self.animation_embed.set_image(url=attach)
                        else:
                            print(f"⚠️ File not found: {self.final_path}")
                            self.file = None
                    except Exception as e:
                        print(f"An error occurred en_com when uploading images: {e}")
                self.animation_embed.colour=discord.Colour.green()
            except Exception as e:
                print(f"An error occurred en_com: {e}")
        else:
            try:
                if self.discord_preview and self.no_preview == False:
                    try: # try to upload the preview images
                        if os.path.isfile(self.final_path):
                            self.file = discord.File(self.final_path,filename="complete_render.png")
                            attach = "attachment://complete_render.png"
                            self.still_embed.set_image(url=attach)
                        else:
                            print(f"⚠️ File not found: {self.final_path}")
                            self.file = None
                    except Exception as e:
                        print(f"An error occurred en_com: {e}")
                self.still_embed.description += "\nRender complete"
                self.still_embed.set_field_at(index=0,name="Job type", value=self.blender_data['job_type'], inline=True)
                self.still_embed.set_field_at(index=2, name="Total time elapsed", value=self.blender_data['total_time_elapsed'], inline=False)
                self.still_embed.colour=discord.Colour.green()
                self.still_embed.set_footer(text="( *︾▽︾)")
            except Exception as e:
                print(f"An error occurred en_com: {e}")    
    
    # Load new data into embeds when the render job is canceled         
    def em_cancel(self,isAnimation):
        if isAnimation: 
            try:
                if "frames_rendered" in self.blender_data:
                    if self.discord_preview and self.no_preview == False:
                        try: # try to upload the preview images
                            if self.blender_data["frames_rendered"] > 1:
                                if os.path.isfile(self.final_first_path):
                                    self.thumbfile=discord.File(self.final_first_path,filename="first_render.png")
                                    thumbattach = "attachment://first_render.png"
                                    self.animation_embed.set_thumbnail(url=thumbattach)
                                else:
                                    print(f"⚠️ File not found: {self.final_first_path}")
                                    self.thumbfile = None
                            else:
                                if os.path.isfile(self.final_path):
                                    # set the image as the complete render
                                    self.file=discord.File(self.final_path,filename="cencel_render.png")
                                    attach = "attachment://cencel_render.png"
                                    self.animation_embed.set_image(url=attach)
                                else:
                                    print(f"⚠️ File not found: {self.final_path}")
                                    self.file = None
                        except Exception as e:
                            print(f"An error occurred en_com: {e}")
                    self.animation_embed.description += "\nCanceled"
                    self.animation_embed.set_field_at(index=3,name="Unfinished Frame", value=self.blender_data['current_frame'], inline=True)
                    self.animation_embed.add_field(name="Still to render", value="("+str(self.blender_data['frames_still_to_render'])+"/"+str(self.blender_data['total_frames'])+")", inline=False)
                    self.animation_embed.add_field(name="Job Cancelled", value=self.blender_data['RENDER_CANCELLED_TIME'], inline=False)
                    self.animation_embed.set_footer(text="[X_ X)")
                    self.animation_embed.colour=discord.Colour.red()
                else:
                    #run if canceled before frist frame starts rendering
                    self.animation_embed.description += "\nCanceled"
                    self.animation_embed.set_field_at(index=3,name="Frame", value=self.blender_data['current_frame'], inline=True)
                    self.animation_embed.add_field(name="Still to render", value="("+str(self.blender_data['frames_still_to_render'])+"/"+str(self.blender_data['total_frames'])+")", inline=False)
                    self.animation_embed.add_field(name="Job Cancelled", value=self.blender_data['RENDER_CANCELLED_TIME'], inline=False)
                    self.animation_embed.set_footer(text="[X_ X)")
                    self.animation_embed.colour=discord.Colour.red()
            except Exception as e:
                print(f"An error occurred in Ani en_cancel: {e}")  
        else: # it's a still render job
            if self.discord_preview and self.no_preview == False:
                try: # try to upload the preview images
                    if os.path.isfile(self.final_path):
                        self.file=discord.File(self.final_path,filename="cencel_render.png")
                        attach = "attachment://cencel_render.png"
                        self.still_embed.set_image(url=attach)
                    else:
                        print(f"⚠️ File not found: {self.final_path}")
                        self.file = None
                except Exception as e:
                    print(f"An error occurred in still en_cancel: {e}")
            self.still_embed.description += "\nCanceled"
            self.still_embed.set_field_at(index=0,name="Job type", value=self.blender_data['job_type'], inline=True)
            self.still_embed.add_field(name="Job Cancelled", value=str(self.blender_data['RENDER_CANCELLED_TIME']), inline=False)
            self.still_embed.set_footer(text="[X_ X)")
            self.still_embed.colour=discord.Colour.red()

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
        self.render_start_countdown = time.time()
        
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
        
        ## Webhook ##
        self.webhook_url = bpy.context.preferences.addons[addon_name].preferences.webhook_url
        self.is_webhook = bpy.context.scene.render_panel_props.is_webhook
        self.webhook_every_frame = bpy.context.scene.render_panel_props.webhook_every_frame
        self.webhook_start = bpy.context.scene.render_panel_props.webhook_start
        self.webhook_first = bpy.context.scene.render_panel_props.webhook_first
        self.webhook_completion = bpy.context.scene.render_panel_props.webhook_completion
        self.webhook_cancel = bpy.context.scene.render_panel_props.webhook_cancel
        
    # Handle render pre logic
    @persistent
    def render_pre(self,scene,*args):
        #print("\nPre Render\n")
        self.current_frame = bpy.context.scene.frame_current
        self.blender_data["frame"] = bpy.context.scene.frame_current
        self.isfirst_frame = self.current_frame == bpy.context.scene.frame_start
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
                    self.blender_data["RENDER_FIRST_FRAME"] = str(self.RENDER_FIRST_FRAME)[:-4]
                    self.blender_data["est_render_job"] = str(self.RENDER_FIRST_FRAME * (self.total_frames - self.counter))[:-4]
                    self.blender_data["frames_left"] = f"{self.total_frames - self.counter}"
                    self.blender_data["frames_rendered"] = self.counter
                    self.blender_data["rendered_frames_percentage"] = round((self.counter / self.total_frames * 100),2)
                    self.blender_data["countdown"] = f"<t:{self.countdown}:R>"
                    self.blender_data["next_frame_countdown"] = f"<t:{self.current_countdown}:R>"
                    
                    if self.discord_preview and self.is_discord: # save first frame is discord preview is enabled
                        first_filename = self.tmp_output_name_frist + self.file_extension
                        self.final_first_path = os.path.join(self.first_rendered_frame_path, first_filename)
                    
                        
                        def delayed_first_frame_save():
                            image = bpy.data.images.get('Render Result')
                            if image and image.has_data:
                                try:
                                    os.makedirs(os.path.dirname(self.final_first_path), exist_ok=True)
                                    image.save_render(self.final_first_path)
                                    #print(f"✅ First frame saved to: {self.final_first_path}")
                                    self.send_webhook_non_blocking(frame=True)
                                except Exception as e:
                                    print(f"❌ Failed to save first frame (render_post): {e}")
                                    self.animation_embed.description += "\nno preview could be saved"
                                    self.no_preview = True
                            else:
                                print("⚠️ Render Result not available for first frame. (render_post)")
                            return None

                        bpy.app.timers.register(delayed_first_frame_save, first_interval=0.2)
                        
                    elif self.is_discord:
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
        if self.current_frame == bpy.context.scene.frame_start:
            None
            # No path is saved yet since the first frame may not be written at this point
        else:
            # Get the file path of the rendered frame
            # `self.rendered_frame_path` stores the absolute path of the currently rendered frame.
            # This is useful for saving or processing the rendered frame during the render process.
            self.rendered_frame_path = bpy.path.abspath(scene.render.frame_path())
    
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
        self.final_path = os.path.join(self.tmp_output_path, final_filename)
        
        # Schedule save if needed
        def delayed_save():
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
                    if self.is_animation:
                        self.animation_embed.description += "\nno preview could be saved"
                    else:
                        self.still_embed.description += "\nno preview could be saved"
                    self.no_preview = True
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
        self.final_path = os.path.join(self.tmp_output_path, final_filename)
        
        # Schedule image saving if preview is requested
        def delayed_save():
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
                    if self.is_animation:
                        self.animation_embed.description += "\nno preview could be saved"
                    else:
                        self.still_embed.description += "\nno preview could be saved"
                    self.no_preview = True
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

notifier_instance = None  # placeholder for later

classes = [
    RenderNotificationsProperties, 
    RenderNotificationsRenderPanel, 
    RenderNotificationsPreferences,
    RenderNotifications_OT_InstallDeps
]

# Register all components and event handlers
def register():
    global Notify, discord, aiohttp, DiscordWebhook, DiscordEmbed
    global notifier_instance # Declare this so we can set it


    # Try to import optional dependencies
    try:
        import discord
        import aiohttp
        from notifypy import Notify as NotifyClass
        from discord import Webhook as DiscordWebhookClass, Embed as DiscordEmbedClass

        Notify = NotifyClass
        DiscordWebhook = DiscordWebhookClass
        DiscordEmbed = DiscordEmbedClass
    except ImportError:
        Notify = None
        discord = None
        aiohttp = None
        DiscordWebhook = None
        DiscordEmbed = None
        print("⚠️ Optional libraries missing: notify-py, discord.py, aiohttp")

    # Register UI and data classes
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.render_panel_props = bpy.props.PointerProperty(type=RenderNotificationsProperties)

    
    # Only register handlers if dependencies are available
    if None not in (Notify, DiscordWebhook, aiohttp):
        notifier_instance = RenderNotifier()
        
        bpy.app.handlers.render_init.append(notifier_instance.render_init)         # Called when render starts
        bpy.app.handlers.render_post.append(notifier_instance.render_post)         # Called after each frame is rendered
        bpy.app.handlers.render_pre.append(notifier_instance.render_pre)           # Called just before rendering starts
        bpy.app.handlers.render_complete.append(notifier_instance.complete)        # Called when render finishes   
        bpy.app.handlers.render_cancel.append(notifier_instance.cancel)            # Called if render is cancelled
        bpy.app.handlers.render_write.append(notifier_instance.on_frame_render)    # Called when a frame is written to disk
    else:
        print("⚠️ Skipping handler registration due to missing libraries.")
        
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