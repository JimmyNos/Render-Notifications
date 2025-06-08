bl_info = {
    "name": "Render Notifications",
    "author": "Jimmy NoStar",
    "version": (0, 1, 8),
    "blender": (4, 3, 2),
    "location": "Render properties",
    "description": "Sends webhooks, discord and desktop notifications to notify you when your render starts, finishes, or is canceled.",
    "category": "All"
}

import time
import bpy # type: ignore
from bpy.types import Operator, AddonPreferences,PropertyGroup,Panel # type: ignore
from bpy.props import StringProperty, IntProperty, BoolProperty # type: ignore
from bpy.app.handlers import persistent # type: ignore

import sys
import subprocess
import os
import json
import requests
import socket

from datetime import datetime
import threading

# Will try to import the required packages, if not installed, it will install them
try:
    from notifypy import Notify
    from discord import Webhook, Embed
    import discord
    import aiohttp
    import asyncio
except ImportError:
    # Install a package to the user site-packages (if not already installed)
    def install_if_missing(package):
        try:
            __import__(package)
        except ImportError:
            print("not imported")
            subprocess.call([sys.executable, "-m", "pip", "install", "--user", package])

    # List of packages to check and install if missing
    for pkg in ["notify-py", "discord", "aiohttp", "asyncio"]:
        install_if_missing(pkg)    
        
    from notifypy import Notify
    from discord import Webhook, Embed
    import discord
    import aiohttp
    import asyncio

#os.system("cls")

# Define the addon preferences class
class RenderNotificationsPreferences(AddonPreferences):
    bl_idname = __name__
    
    ## Desktop ##
    custom_sound: BoolProperty( #type: ignore
        name="Use Custom sound file",
        description="Use a custom file for desktop notifications.",
        default=False,
    )
    desktop_sound_path: StringProperty( #type: ignore
        name="Path to sound file",
        description="Use a custom wav file for desktop notification sound.",
        subtype = "FILE_PATH",
        options = {"LIBRARY_EDITABLE"},
        maxlen = 1024
    )
    
    ## Discord ##
    discord_webhook_name: StringProperty( #type: ignore
        name="channel webhook name",
        description="Name of discotrd bot that will send the notifications.",
        default="Render Bot" # remove before release!
    )
    discord_webhook_url: StringProperty( #type: ignore
        name="Discord channel webhook url",
        description="Discord channel webhook url to send notifications to.",
        default="https://discord.com/api/webhooks/1346076038387732480/50d-BremraDRbSfeHpvnbOYzpaFbhBskjEwj8uYj4u3sVDzwmH54XYHg5prAJpOMqhvy" # remove before release!
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
        description="Webhook url to send notifications to.",
        default="https://mosakohome.duckdns.org:8123/api/webhook/-blender3XsCcti0V19vzX-" # remove before release!
    )
    
    # Drawing UI for addon preferences
    def draw(self, context):
        layout = self.layout
        layout.label(text="Setup notifications")
        
        ## Desktop ##
        layout.label(text="Desktop notifications")
        row = layout.row()
        row.label(text="Custom Sound:")
        row.prop(self, "custom_sound", text="")
        row = layout.row()
        row.label(text="Sound path:")
        row.prop(self, "desktop_sound_path", text="")
        
        ## Discord ##
        layout.label(text="")
        layout.label(text="Discord notifications")
        row = layout.row()
        row.label(text="Discord channel webhook name:")
        row.prop(self, "discord_webhook_name", text="")
        row = layout.row()
        row.label(text="Discord channel webhook url:")
        row.prop(self, "discord_webhook_url", text="")
        row = layout.row()
        row.label(text="Default temporary save location:")
        row.prop(self, "tmp_output_path", text="")
        
        ## Webhook ##
        layout.label(text="")
        layout.label(text="Webhook notifications")
        row = layout.row()
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
    """Creates a Panel in the render properties tab"""
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
        #self.desktop = True
        #self.discord_webhook = True
        #self.webhook = True
        #self.notified = False
        self.blend_filepath = None
        self.blend_filename = None
        self.is_animation = False
        self.total_frames = 0
        self.avarage_est_frames = []
        #self.FRAME_START_TIME = None
        self.RENDER_START_TIME = None
        self.RENDER_PRE_TIME = None
        self.RENDER_TOTAL_TIME = None
        self.RENDER_FRIST_FRAME = None
        self.RENDER_CURRENT_FRAME = None
        self.RENDER_CANCELLED_TIME = None
        #self.total_rendered = ""
        #self.total_to_render = ""
        #self.total_render_time = ""
        self.avarage_time = 0
        self.job_type = ""
        self.blender_data = {}
        self.current_frame = None
        self.counter = 0
        self.precountdown = 0.0
        self.message_id = None
        
        self.file = None
        #self.thumbfile = None
        self.no_preview = False
        self.rendered_frame_path = ""
        #self.first_rendered_frame_path = ""
        self.file_extension = ".png"
        
        self.embed = Embed(title="🎬 Blender Render Status", description="Initializing...", colour=0x3498db)   
        self.still_embed = discord.Embed(type="rich", color=discord.Color.gold())
        self.first_frame_embed = discord.Embed(type="rich", color=discord.Color.gold())
        self.animation_embed = discord.Embed(type="rich", color=discord.Color.gold())

        self.end = False
        # Start an asyncio event loop in a separate thread
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.run_async_loop, daemon=True).start()
    
    # reset variables on render initialization
    # this is called when the render job starts
    def clean_var(self):
        self.is_animation = False
        self.total_frames = 0
        self.avarage_est_frames = []
        #self.FRAME_START_TIME = None
        self.RENDER_START_TIME = None
        self.RENDER_PRE_TIME = None
        self.RENDER_TOTAL_TIME = None
        self.RENDER_FRIST_FRAME = None
        self.RENDER_CURRENT_FRAME = None
        self.RENDER_CANCELLED_TIME = None
        self.total_frames = 0
        #self.total_rendered = ""
        #self.total_to_render = ""
        #self.total_render_time = ""
        self.avarage_time = 0
        self.job_type = ""
        self.blender_data = {}
        self.current_frame = None
        self.counter = 0
        self.precountdown = 0.0
        
        self.tmp_output_name = ""
        self.tmp_output_name_frist = ""
    
    # run the asyncio event loop in a separate thread
    # this is for the discord webhook
    def run_async_loop(self):
        """Runs the asyncio event loop in a separate thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        if self.end:
            self.loop.stop()
    
    # Send a new discord message or edit embeded message
    async def send_or_update_embed(self, init=False, frame=False, finished=False, canceled=False):
        """Send a new webhook message or update the existing one."""
        if init:
            if self.blender_data['job_type'] == "Aniamtion": 
                self.em_init(True)
            else: 
                self.em_init(False)  
            
        elif frame:
            if self.blender_data['job_type'] == "Aniamtion": 
                self.em_post(True)
            else: 
                self.em_post(False)
                    
        elif finished:
            if self.blender_data['job_type'] == "Aniamtion": 
                self.em_complete(True)
                print("animation finishing...")
            else: 
                self.em_complete(False)
                
        elif canceled:
            if self.blender_data['job_type'] == "Aniamtion": 
                self.em_cancel(True)
            else: 
                self.em_cancel(False)
        
        
        # Hanlde sending this discord webhook message
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(self.discord_webhook_url, session=session)
            if self.message_id:
                # If message_id is set, edit the existing message
                try:
                    full_hook = await webhook.fetch()
                    if self.blender_data['job_type'] == "Aniamtion": 
                        # If the preview is enabled, send the embed with the preview images
                        if self.discord_preview:
                            try:
                                if finished:
                                    await webhook.edit_message(self.message_id, embed=self.animation_embed,attachments=[self.file,self.thumbfile])
                                    
                                    await self.send_on_complete(full_hook, webhook)
                                elif canceled:
                                    await webhook.edit_message(self.message_id, embed=self.animation_embed,attachments=[self.file,self.thumbfile])
                                    
                                    await self.send_on_cancel(full_hook, webhook)
                                elif self.blender_data["frames_rednered"] == 1:
                                    await webhook.edit_message(self.message_id, embed=self.first_frame_embed,attachments=[self.file])
                                else:
                                    await webhook.edit_message(self.message_id, embed=self.animation_embed)
                            except Exception as e:
                                # If the embed is too large or an error is cought, try to send it without the image
                                print(f"error. failed with image embed: {e}")
                                self.animation_embed.description+= "\n render too large for preview or failed to save."
                                if finished:
                                    await webhook.edit_message(self.message_id, embed=self.animation_embed)
                                    
                                    await self.send_on_complete(full_hook, webhook)
                                elif canceled:
                                    await webhook.edit_message(self.message_id, embed=self.animation_embed)
                                    
                                    await self.send_on_cancel(full_hook, webhook)
                                elif self.blender_data["frames_rednered"] == 1:
                                    await webhook.edit_message(self.message_id, embed=self.first_frame_embed)
                                else:
                                    await webhook.edit_message(self.message_id, embed=self.animation_embed)
                        else:
                            if finished:
                                await webhook.edit_message(self.message_id, embed=self.animation_embed)
                                
                                await self.send_on_complete(full_hook, webhook)
                            elif canceled:
                                await webhook.edit_message(self.message_id, embed=self.animation_embed)
                                
                                await self.send_on_cancel(full_hook, webhook)
                            elif self.blender_data["frames_rednered"] == 1:
                                await webhook.edit_message(self.message_id, embed=self.first_frame_embed)
                            else:
                                await webhook.edit_message(self.message_id, embed=self.animation_embed)
                    else:
                        # Send still embed if the job is not an animation
                        try:
                            if finished and self.discord_preview:
                                await webhook.edit_message(self.message_id, embed=self.still_embed,attachments=[self.file])
                                
                                await self.send_on_complete(full_hook, webhook)
                            elif canceled and self.discord_preview:
                                await webhook.edit_message(self.message_id, embed=self.still_embed,attachments=[self.file])
                                
                                await self.send_on_cancel(full_hook, webhook)
                            else:
                                await webhook.edit_message(self.message_id, embed=self.still_embed)
                        except:
                            # If the embed is too large or an error is cought, try to send it without the image
                            self.still_embed.description+= "\n image too large for preview"
                            if finished:
                                await webhook.edit_message(self.message_id, embed=self.still_embed)
                                
                                await self.send_on_complete(full_hook, webhook)
                            elif canceled:
                                await webhook.edit_message(self.message_id, embed=self.still_embed)
                                
                                await self.send_on_cancel(full_hook, webhook)
                            else:
                                await webhook.edit_message(self.message_id, embed=self.still_embed)
                    
                    # If the job is finished or canceled, clear the message_id                  
                    if canceled or finished:
                        #self.animation_embed.clear_fields()
                        #self.still_embed.clear_fields()
                        self.message_id = None
                        
                except Exception as e:
                    print(f"⚠️ Error updating message: {e}")
                    
            else: # if message_id is not set, send a new message
                if self.blender_data['job_type'] == "Aniamtion": 
                    msg = await webhook.send(embed=self.first_frame_embed, username=self.discord_webhook_name, wait=True)
                    self.message_id = msg.id
                    
                else:
                    if self.isfirst_frame:
                        msg = await webhook.send(embed=self.first_frame_embed, username=self.discord_webhook_name, wait=True)
                    msg = await webhook.send(embed=self.still_embed, username=self.discord_webhook_name, wait=True)
                    self.message_id = msg.id
    
    # Send a discord message when the render job is complete         
    async def send_on_complete(self, full_hook=None, webhook=None):
        print(f"full_hook.guild_id: {full_hook.guild_id}, full_hook.channel_id: {full_hook.channel_id}, self.message_id: {self.message_id}")
        message_link = f"https://discord.com/channels/{full_hook.guild_id}/{full_hook.channel_id}/{self.message_id}"
        reply_content = f"{message_link}"
        print(f"reply_content: {reply_content}")
        self.complete_embed.description += f"\n## {reply_content}"
        await webhook.send(username=self.discord_webhook_name, embed=self.complete_embed)
        print("reply sent")
    
    # Send a discord message when the render job is canceled
    async def send_on_cancel(self, full_hook=None, webhook=None):
        print(f"full_hook.guild_id: {full_hook.guild_id}, full_hook.channel_id: {full_hook.channel_id}, self.message_id: {self.message_id}")
        message_link = f"https://discord.com/channels/{full_hook.guild_id}/{full_hook.channel_id}/{self.message_id}"
        reply_content = f"{message_link}"
        print(f"reply_content: {reply_content}")
        self.cancel_embed.description += f"\n## {reply_content}"
        await webhook.send(username=self.discord_webhook_name, embed=self.cancel_embed)
        print("reply sent")
    
    # handle discord webhook using a separate thread-safe event loop
    def send_webhook_non_blocking(self, init=False, frame=False, finished=False, canceled=False):
        """Schedule webhook execution using a separate thread-safe event loop."""
        future = asyncio.run_coroutine_threadsafe(
            self.send_or_update_embed(init, frame, finished, canceled),
            self.loop
        )
        future.result()  # Ensure the coroutine executes correctly

    # Load data into embeds
    def em_init(self,isAniamtion):
        
        #global blender, render_embed
        # create the embed messages
        self.animation_embed = Embed(title=self.blender_data['project_name'], 
                                     description=f"Starting render job.. <t:{int(self.render_start_countdown)}:R>", 
                                     colour=discord.Colour.blue())
        
        self.still_embed = Embed(title=self.blender_data['project_name'], 
                                 description=f"Starting render job.. <t:{int(self.render_start_countdown)}:R>", 
                                 colour=discord.Colour.gold())
        
        self.first_frame_embed = Embed(title=self.blender_data['project_name'], 
                                       description=f"Starting render job.. <t:{int(self.render_start_countdown)}:R>", 
                                       colour=discord.Colour.blue())
        
        self.complete_embed = Embed(title="*Render completed :checkered_flag: :white_check_mark:*", 
                               description=f"Render job for {self.blender_data['project_name']} completed successfully!", 
                               colour=discord.Colour.light_embed(),
                               timestamp=discord.utils.utcnow())
        
        self.cancel_embed = Embed(title="*Render canceled :flag_black: :anger: :x:*", 
                               description=f"Render job for {self.blender_data['project_name']} was cancel!", 
                               colour=discord.Colour.light_embed(),
                               timestamp=discord.utils.utcnow())
        
        print("Starting")
        
        # set the embed fields with the data genarated from blender   
        if isAniamtion: 
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
            #self.render_embed.set_field_at(index=3,name="Frame edit", value=blender['frame'], inline=False)
            
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
    def em_post(self,isAniamtion):
        
        print("\nrendering")    
        print(f"Current fields complere: {self.animation_embed.fields}")

        print(f"Trying to set field at index 3 with frame: {self.blender_data['frame']}")

        if isAniamtion: 
            print(self.blender_data["frames_rednered"])
            
            self.frames_rendered_feild = "("+str(self.blender_data['frames_rednered'])+"/"+str(self.blender_data['total_frames'])+") "+str(self.blender_data['rednered_frames_percentage'])+"%"
            print(self.frames_rendered_feild)
            
            #check if it's the first frame
            if self.blender_data["frames_rednered"] == 1:
                try:
                    self.file=discord.File(self.first_rendered_frame_path,filename="first_render.png")
                    atach = "attachment://first_render.png"
                    print(atach)
                    self.animation_embed.set_thumbnail(url=atach)
                    self.first_frame_embed.set_thumbnail(url=atach)
                except Exception as e:
                    print(f"An error occurred en_com: {e}")
                    
                
                
                self.animation_embed.description += "\nFrist frame rendered"
                self.animation_embed.set_field_at(index=3,name="Frame", value=self.blender_data['frame'], inline=False)
                self.animation_embed.set_field_at(index=4,name="frames rendered", value=self.frames_rendered_feild, inline=True)
                self.animation_embed.set_field_at(index=5,name="Frame time", value=self.blender_data['RENDER_FRIST_FRAME'], inline=True)
                self.animation_embed.set_field_at(index=6,name="Est. next frame", value=self.blender_data['next_frame_countdown'], inline=True)
                self.animation_embed.set_field_at(index=8,name="Est. render job" + self.blender_data['countdown'], value=self.blender_data['est_render_job'], inline=False)
                self.animation_embed.colour=discord.Colour.gold()
                
                self.animation_embed.set_footer(text= "(。>︿<)_θ")
            else:
                self.animation_embed.set_field_at(index=3,name="Frame", value=self.blender_data['frame'], inline=False)
                self.animation_embed.set_field_at(index=4,name="frames rendered", value=self.frames_rendered_feild, inline=True)
                self.animation_embed.set_field_at(index=5,name="Frame time", value=self.blender_data['RENDER_CURRENT_FRAME'], inline=True)
                self.animation_embed.set_field_at(index=6,name="Est. next frame", value=self.blender_data['next_frame_countdown'], inline=True)
                self.animation_embed.set_field_at(index=7,name="Avarage per frame", value=f"{self.blender_data['avarage_time']}", inline=True)
                self.animation_embed.set_field_at(index=8,name="Est. render job" + self.blender_data['countdown'], value=self.blender_data['est_render_job'], inline=False)
      
    # Load new data into embeds when the render job is complete  
    def em_complete(self,isAniamtion):
        
        print("\ncompleting render job")
        if isAniamtion: 
            try:
                try: # try to upload the preview images
                    print(f"Current fields complete: {self.animation_embed.fields}")
                    print("in encomplete an: "+ self.tmp_output_path)
                    self.file=discord.File(self.tmp_output_path,filename="complete_render.png")
                    atach = "attachment://complete_render.png"
                    self.thumbfile=discord.File(self.first_rendered_frame_path,filename="first_render.png")
                    thumbatach = "attachment://first_render.png"
                    self.animation_embed.set_thumbnail(url=thumbatach)

                    print(atach)
                    self.animation_embed.set_image(url=atach)
                except Exception as e:
                    print(f"An error occurred en_com when uploading images: {e}")
                self.animation_embed.description += "\nRender complete"
                self.animation_embed.set_field_at(index=7, name="Avarage per frame", value=self.blender_data['avarage_time'], inline=True)
                self.animation_embed.set_field_at(index=9, name="Total est. time", value=self.blender_data['total_Est_time'], inline=True)
                self.animation_embed.set_field_at(index=10, name="Total time elapsed", value=self.blender_data['total_time_elapsed'], inline=True)
                self.animation_embed.set_footer(text="( *︾▽︾)")
                self.animation_embed.colour=discord.Colour.green()
            except Exception as e:
                print(f"An error occurred en_com: {e}")
        else:
            try:
                try: # try to upload the preview images
                    print(self.tmp_output_path)
                    self.file=discord.File(self.tmp_output_path,filename="render.png")
                    atach = "attachment://render.png"
                    print(atach)
                    self.still_embed.set_image(url=atach)
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
    def em_cancel(self,isAniamtion):
        
        print("em_cancel")
            
        if isAniamtion: 
            try:
                if "frames_rednered" in self.blender_data:
                    try: # try to upload the preview images
                        if self.blender_data["frames_rednered"] > 1:
                            if self.no_preview == False:
                                self.thumbfile=discord.File(self.first_rendered_frame_path,filename="first_render.png")
                                thumbatach = "attachment://first_render.png"
                                self.animation_embed.set_thumbnail(url=thumbatach)
                        else:
                            if self.self.no_preview == False:
                                self.file=discord.File(self.tmp_output_path,filename="cencel_render.png")
                                atach = "attachment://cencel_render.png"
                                print(atach)
                                self.animation_embed.set_image(url=atach)
                    except Exception as e:
                        print(f"An error occurred en_com: {e}")
                    self.animation_embed.description += "\nCanceled"
                    self.animation_embed.set_field_at(index=3,name="Frame", value=self.blender_data['current_frame'], inline=True)
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
                print(f"An error occurred in cancel: {e}")  
        else:
            try: # try to upload the preview images
                print(self.tmp_output_path)
                self.file=discord.File(self.tmp_output_path,filename="cencel_render.png")
                atach = "attachment://cencel_render.png"
                print(atach)
                self.still_embed.set_image(url=atach)
            except Exception as e:
                print(f"An error occurred en_com: {e}")
            self.still_embed.description += "\nCanceled"
            self.still_embed.set_field_at(index=0,name="Job type", value=self.blender_data['job_type'], inline=True)
            self.still_embed.add_field(name="Job Cancelled", value=str(self.blender_data['RENDER_CANCELLED_TIME']), inline=False)
            self.still_embed.set_footer(text="[X_ X)")
            self.still_embed.colour=discord.Colour.red()

    # Handle render logic
    @persistent
    def render_init(self,scene,*args):
        self.clean_var() # clears the variables for a new render job
        
        #get blend file name
        self.blend_filepath = bpy.data.filepath
        self.blend_filename = os.path.basename(self.blend_filepath) if self.blend_filepath else "Untitled.blend"
        self.blend_filename = self.blend_filename[:-6]
        self.tmp_output_name = self.blend_filename
        self.tmp_output_name_frist = self.blend_filename + " first frame"
        
        self.RENDER_START_TIME = datetime.now()
        self.render_start_countdown = time.time()
        
        self.total_frames = bpy.context.scene.frame_end - bpy.context.scene.frame_start + 1
        
        self.blender_data["call_type"] = "render_init"
        self.blender_data["project_name"] = self.blend_filename
        self.blender_data["total_frames"] = self.total_frames
        
        
        ## Desktop ##
        self.is_custom_sound = bpy.context.preferences.addons[__name__].preferences.custom_sound
        self.desktop_sound_path = bpy.context.preferences.addons[__name__].preferences.desktop_sound_path
        self.is_desktop = bpy.context.scene.render_panel_props.is_desktop
        self.desktop_start = bpy.context.scene.render_panel_props.desktop_start
        self.desktop_first = bpy.context.scene.render_panel_props.desktop_first
        self.desktop_completion = bpy.context.scene.render_panel_props.desktop_completion
        self.desktop_cancel = bpy.context.scene.render_panel_props.desktop_cancel
        
        ## Discord ##
        ## Check if tmp_output_path is the same as discord_preview_path
        #if bpy.context.preferences.addons[__name__].preferences.tmp_output_path == bpy.context.scene.render_panel_props.discord_preview_path:
        #    self.tmp_output_path = bpy.context.preferences.addons[__name__].preferences.tmp_output_path
        #    print("tmp_output_path is the same as discord_preview_path")
        #elif bpy.context.preferences.addons[__name__].preferences.tmp_output_path != bpy.context.scene.render_panel_props.discord_preview_path:
        #    self.tmp_output_path = bpy.context.scene.render_panel_props.discord_preview_path
        #    print("tmp_output_path is NOT the same as discord_preview_path")
        print(f"preferences path: {bpy.context.preferences.addons[__name__].preferences.tmp_output_path}")
        print(f"render_panel_props path: {bpy.context.scene.render_panel_props.discord_preview_path}")
        # Check if the user wants to use a custom preview path
        if bpy.context.scene.render_panel_props.use_custom_preview_path:
            self.tmp_output_path = bpy.context.scene.render_panel_props.discord_preview_path
            print("Using custom preview path")
        else:
            self.tmp_output_path = bpy.context.preferences.addons[__name__].preferences.tmp_output_path
            print("Using preferences default preview path")
        print(f"tmp_output_path: {self.tmp_output_path}")
        
        self.first_rendered_frame_path = bpy.context.preferences.addons[__name__].preferences.tmp_output_path
        self.discord_webhook_name = bpy.context.preferences.addons[__name__].preferences.discord_webhook_name
        self.discord_webhook_url = bpy.context.preferences.addons[__name__].preferences.discord_webhook_url
        self.is_discord = bpy.context.scene.render_panel_props.is_discord
        self.discord_preview = bpy.context.scene.render_panel_props.discord_preview
        
        ## Webhook ##
        self.webhook_url = bpy.context.preferences.addons[__name__].preferences.webhook_url
        self.is_webhook = bpy.context.scene.render_panel_props.is_webhook
        self.webhook_every_frame = bpy.context.scene.render_panel_props.webhook_every_frame
        self.webhook_start = bpy.context.scene.render_panel_props.webhook_start
        self.webhook_first = bpy.context.scene.render_panel_props.webhook_first
        self.webhook_completion = bpy.context.scene.render_panel_props.webhook_completion
        self.webhook_cancel = bpy.context.scene.render_panel_props.webhook_cancel
        
        print("\nStarting Render\n")
        print(bpy.context.scene.frame_current)
            
        print(self.blender_data)
 
    # Handle render pre logic
    @persistent
    def render_pre(self,scene,*args):
        print("\nPre Render\n")
        self.current_frame = bpy.context.scene.frame_current
        self.blender_data["frame"] = bpy.context.scene.frame_current
        self.isfirst_frame = self.current_frame == bpy.context.scene.frame_start
        print(self.current_frame)
        
        # check if the render job is an animation or a still image
        if self.current_frame == bpy.context.scene.frame_start:
            self.is_animation = True
            self.job_type = "Aniamtion"  
            self.blender_data["job_type"] = self.job_type
            self.blender_data["frame"] = self.current_frame
            self.blender_data["frame_range"] = f"{bpy.context.scene.frame_start} - {bpy.context.scene.frame_end}"
            self.blender_data["Total_frames_to_render"] = self.total_frames
            #send_message_to_bot(blender_data)
            
            if self.is_discord:
                self.send_webhook_non_blocking(init=True)
            
            if self.is_webhook and self.webhook_start:
                self.send_webhook()
                
            if self.is_desktop and self.desktop_start:
                self.notifi_desktop(
                    title="Render started", 
                    message="Render job started for: " + self.blender_data["project_name"]
                    )
                print("desktop checked")
        
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
                print("desktop checked")
    
    # Handle render post logic
    @persistent   
    def render_post(self,scene,*args):
        print("\nPost Render\n")
        
        # Track call type for logging or webhook purposes
        self.blender_data["call_type"] = "render_post"
        
        self.current_frame = bpy.context.scene.frame_current
        first_frame = False
        if self.is_animation:
            # Check if this is the first frame of the animation
            print(self.current_frame == bpy.context.scene.frame_start)
            first_frame = self.current_frame == bpy.context.scene.frame_start
            if first_frame:
                print("its the frist frame")
                self.RENDER_FRIST_FRAME = datetime.now() - self.RENDER_START_TIME
                
                # Estimate average time per frame and total job duration
                self.precountdown = time.time() - self.render_start_countdown
                self.countdown = int(time.time() + self.precountdown * (self.total_frames - self.counter))
                self.current_countdown = int(time.time() + self.precountdown)
                self.precountdown = time.time()
                
                print(self.RENDER_FRIST_FRAME.seconds)
                self.avarage_est_frames.append(self.RENDER_FRIST_FRAME)
                self.RENDER_PRE_TIME = datetime.now()
                self.counter += 1
                
                # Save the first rendered frame as an PNG image
                image = bpy.data.images['Render Result']
                self.tmp_output_name_frist += self.file_extension
                self.first_rendered_frame_path += self.tmp_output_name_frist
                print(self.first_rendered_frame_path)
                image.save_render(self.first_rendered_frame_path)
                print(self.first_rendered_frame_path)
                
                # Populate render info for sending to Discord or display
                self.blender_data["RENDER_FRIST_FRAME"] = str(self.RENDER_FRIST_FRAME)[:-4]
                self.blender_data["est_render_job"] = str(self.RENDER_FRIST_FRAME * (self.total_frames - self.counter))[:-4]
                self.blender_data["frames_left"] = f"{self.total_frames - self.counter}"
                self.blender_data["frames_rednered"] = self.counter
                self.blender_data["rednered_frames_percentage"] = round((self.counter / self.total_frames * 100),2)
                self.blender_data["countdown"] = f"<t:{self.countdown}:R>"
                self.blender_data["next_frame_countdown"] = f"<t:{self.current_countdown}:R>"
                
                print(self.blender_data)
            else:
                try:
                    # Time per frame and ETA calculations
                    print("its not the frist frame")
                    self.precountdown = time.time() - self.precountdown
                    self.countdown = int(time.time() + self.precountdown * (self.total_frames - self.counter))
                    self.current_countdown = int(time.time() + self.precountdown)
                    self.counter += 1
                    self.RENDER_CURRENT_FRAME = datetime.now() - self.RENDER_PRE_TIME
                    self.avarage_est_frames.append(self.RENDER_CURRENT_FRAME) 
                    self.RENDER_PRE_TIME = datetime.now()
                    self.precountdown = time.time()
                    
                    # Estimate remaining time
                    if self.total_frames != self.counter:
                        self.blender_data["est_render_job"] = str(self.RENDER_CURRENT_FRAME * (self.total_frames - self.counter))[:-4]
                    else:
                        self.blender_data["est_render_job"] = str(self.RENDER_CURRENT_FRAME * (self.total_frames - self.counter + 1))[:-4]
                        
                    # Update per-frame render data
                    self.blender_data["frame"] = bpy.context.scene.frame_current
                    self.blender_data["RENDER_CURRENT_FRAME"] = str(self.RENDER_CURRENT_FRAME)[:-4]
                    self.blender_data["frames_left"] = f"{self.total_frames - self.counter}"
                    self.blender_data["frames_rednered"] = self.counter
                    self.blender_data["rednered_frames_percentage"] = round((self.counter / self.total_frames * 100),2)
                    self.blender_data["countdown"] = f"<t:{self.countdown}:R>"
                    self.blender_data["next_frame_countdown"] = f"<t:{self.current_countdown}:R>"

                except Exception as e:
                    print(e)
                    print("its a still render job")
            
            print(self.RENDER_FRIST_FRAME)
            
            print(self.avarage_est_frames)
            print(len(self.avarage_est_frames))
            
            # Calculate running average frame render time
            avg = datetime.now() - datetime.now()
            for est in self.avarage_est_frames:
                avg += est / len(self.avarage_est_frames)
            frame = scene.frame_current
            
            self.avarage_time = avg
            self.blender_data["avarage_time"] = str(self.avarage_time)[:-4]
            #send_message_to_bot(blender_data)
            if self.is_discord:
                self.send_webhook_non_blocking(frame=True)
            
            if self.is_webhook and first_frame and self.webhook_first:
                self.send_webhook()
            elif self.webhook_every_frame:
                self.send_webhook()
            
            if self.is_desktop and first_frame and self.desktop_first:
                self.notifi_desktop(
                    title="First frame rendered", 
                    message=f"First frame rendered for: {self.blender_data['project_name']} \ntime: {self.blender_data['RENDER_FRIST_FRAME']} \nEst. render job: {self.blender_data['est_render_job']}"
                    )
                print("desktop checked")
            print(self.blender_data)
            
            print(self.avarage_time)

    # check if rendering frame is the first frame in the timeline
    @persistent
    def on_frame_render(self,scene, *args):
        print("\nOn Frame Render\n")
        # Check if this is the first frame of the animation
        if self.current_frame == bpy.context.scene.frame_start:
            None
            print("is first frame")
            # No path is saved yet since the first frame may not be written at this point
        else:
            # Get the file path of the rendered frame
            self.rendered_frame_path = bpy.path.abspath(scene.render.frame_path())

        print(f"Frame saved at: {self.rendered_frame_path}")
    
    #handle render complete logic
    @persistent
    def complete(self,scene,*args):
        print("\nRender Complete\n")
        
        # Track total time taken for the entire render
        self.RENDER_TOTAL_TIME = datetime.now() - self.RENDER_START_TIME
        self.blender_data["call_type"] = "complete"
        
        scene = bpy.context.scene
        print(self.tmp_output_path)
        
        # Detect if the render was a still frame (only one frame rendered)
        if self.current_frame == bpy.context.scene.frame_start:
            self.is_animation = False
            self.job_type = "Still"
            self.blender_data["job_type"] = self.job_type
            print("comp is first frame")
        
        if self.is_animation:
            # Save last frame of the animation
            image = bpy.data.images['Render Result']
            self.tmp_output_name += self.file_extension
            self.tmp_output_path += self.tmp_output_name
            image.save_render(self.tmp_output_path)
            
            # Update metadata
            self.blender_data["avarage_time"] = str(self.avarage_time)[:-4]
            self.blender_data["total_Est_time"] = str(self.RENDER_FRIST_FRAME * self.total_frames)[:-4]
            self.blender_data["total_time_elapsed"] = str(self.RENDER_TOTAL_TIME)[:-4]
        else:
            # Save still image
            image = bpy.data.images['Render Result']
            self.tmp_output_name += self.file_extension
            print(f"tmp_output_name:{self.tmp_output_name}")
            self.tmp_output_path += self.tmp_output_name
            print(f"tmp_output_path:{self.tmp_output_path}")
            image.save_render(self.tmp_output_path)
            
            self.blender_data["total_time_elapsed"] = str(self.RENDER_TOTAL_TIME)[:-4]
        
        if self.is_discord:
            self.send_webhook_non_blocking(finished=True)
        
        if self.is_webhook and self.webhook_completion:
            self.send_webhook()
            
        if self.is_desktop and self.desktop_completion:
            self.notifi_desktop(
                title="Render completed", 
                message=f"Render job completed for: {self.blender_data['project_name']} \nTotal time elapsed: {self.blender_data['total_time_elapsed']}"
                )
            print("desktop checked")
        
        # Reset flags
        self.is_animation = False
        
        print("\n===== Render Completed =====")
        print(f"Blend File Name: {self.blend_filename}")
        print(f"Total Render Time: {self.RENDER_TOTAL_TIME}")
        print(f"Total Frames: {self.total_frames}")
        print(f"first Frame: {bpy.context.scene.frame_start}")
        print(f"Average Render Time per Frame: {self.avarage_time}")
        print(f"First Frame Render Time: {self.RENDER_FRIST_FRAME}")
        print("==========================\n")
        
        print(self.blender_data)

    #handle render cancel logic
    @persistent
    def cancel(self,scene,*args):
        # Calculate how long the render was running before it was cancelled
        self.RENDER_CANCELLED_TIME = datetime.now() - self.RENDER_START_TIME
        
        # Capture the current frame at cancellation
        cancel_frame = self.current_frame
        self.blender_data["call_type"] = "cancel"
        
        scene = bpy.context.scene
        render = scene.render
        print(self.tmp_output_path)
        
        # Detect if the render was a still frame (only one frame rendered)
        if self.current_frame == bpy.context.scene.frame_start:
            self.is_animation = False
            self.job_type = "Still"
            self.blender_data["job_type"] = self.job_type
            print("comp is first frame")
        
        if self.is_animation:
            # Handle animation render cancellation
            render_path = render.filepath
            print(render_path)
            image = bpy.data.images['Render Result']
            
            try:
                # Attempt to save the last rendered frame
                self.tmp_output_path += self.tmp_output_name
                image.save_render(self.tmp_output_path)
            except Exception as e:
                print(f"error while saving image: {e}")
                self.animation_embed.description += "\nno priview could be saved"
                self.no_preview = True
            
            self.blender_data["current_frame"] = cancel_frame
            self.blender_data["total_frames_rendered"] = bpy.context.scene.frame_end - cancel_frame
            self.blender_data["frames_still_to_render_range"] = f"{cancel_frame} - {bpy.context.scene.frame_end}"
            self.blender_data["frames_still_to_render"] = f"{bpy.context.scene.frame_end - self.current_frame}"
            self.blender_data["RENDER_CANCELLED_TIME"] = str(self.RENDER_CANCELLED_TIME)[:-4]
            
        else:
            # Handle still image cancellation
            image = bpy.data.images['Render Result']
            
            self.tmp_output_name += self.file_extension
            self.tmp_output_path += self.tmp_output_name
            image.save_render(self.tmp_output_path)
            
            self.blender_data["RENDER_CANCELLED_TIME"] = str(self.RENDER_CANCELLED_TIME)[:-4]
        
        if self.is_discord:
            self.send_webhook_non_blocking(canceled=True)
        
        if self.is_webhook and self.webhook_cancel:
            self.send_webhook()
            
        if self.is_desktop and self.desktop_cancel:
            self.notifi_desktop(
                title="Render canceled", 
                message=f"Render job canceled for: {self.blender_data['project_name']} \nRender canceled after: {self.RENDER_CANCELLED_TIME}"
                )
            print("desktop checked")
            
        print("Render Canceled After:", self.RENDER_CANCELLED_TIME)
        print(self.blender_data)


    # Send JSON payload via webhook to a server (e.g., Flask, Home Assistant, etc.)
    @persistent
    def send_webhook(self):
        # Use the preconfigured self.webhook_url
        payload = self.blender_data
        print(payload)
        try:
            
            response = requests.post(self.webhook_url, json=payload)
            
            if response.status_code == 200:
                print('Webhook sent successfully!')
                print(response)
            else:
                print(f'Failed to send webhook. Status code: {response.status_code}')
                print(response.text)
        except Exception as e:
            print(f"⚠️ Exception while sending webhook: {e}")
    
    @persistent
    def notifi_desktop(self,*args,title,message):
        print("\n Notifing via desktop \n")
        notification = Notify()
        notification.title = title
        notification.message = message
        
        # Optionally play a custom sound if enabled
        if self.is_custom_sound:
            notification.audio = self.desktop_sound_path
        
        try:
            notification.send()
        except Exception as e:
            print(f"⚠️ Failed to send desktop notification: {e}")

# Create an instance of the notifier class
notifier = RenderNotifier()

# List of custom classes to register (e.g. UI panels, properties, preferences)
#@persistent
classes = [
    RenderNotificationsProperties, 
    RenderNotificationsRenderPanel, 
    RenderNotificationsPreferences
]

# Register all components and event handlers
def register():
    # Register custom classes (panel, properties, preferences)
    for cls in classes:
        bpy.utils.register_class(cls)
        
    # Add the custom property group to the Scene type
    bpy.types.Scene.render_panel_props = bpy.props.PointerProperty(type=RenderNotificationsProperties)

    # Attach custom handlers to Blender's render events
    bpy.app.handlers.render_init.append(notifier.render_init)       # Called when render starts
    bpy.app.handlers.render_post.append(notifier.render_post)       # Called after each frame is rendered
    bpy.app.handlers.render_pre.append(notifier.render_pre)         # Called just before rendering starts
    bpy.app.handlers.render_complete.append(notifier.complete)      # Called when render finishes
    bpy.app.handlers.render_cancel.append(notifier.cancel)          # Called if render is cancelled
    bpy.app.handlers.render_write.append(notifier.on_frame_render)  # Called when a frame is written to disk
    
# Unregister all components and handlers
def unregister():
    # Unregister in reverse order to prevent dependency issues
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    # Remove the custom property from the Scene type
    del bpy.types.Scene.render_panel_props
    
    # Detach all event handlers
    bpy.app.handlers.render_init.remove(notifier.render_init)
    bpy.app.handlers.render_post.remove(notifier.render_post)
    bpy.app.handlers.render_pre.remove(notifier.render_pre)
    bpy.app.handlers.render_complete.remove(notifier.complete)
    bpy.app.handlers.render_cancel.remove(notifier.cancel)
    bpy.app.handlers.render_write.remove(notifier.on_frame_render)

# Run registration when script is executed directly
if __name__ == "__main__":
    register()