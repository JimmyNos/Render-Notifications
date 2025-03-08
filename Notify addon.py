import time
import bpy # type: ignore

import sys
import subprocess
import os
import json
import requests
import socket

from datetime import datetime


try:
    from notifypy import Notify
    from discord import Webhook, Embed
    import discord
    import threading
    import aiohttp
    import asyncio
except ImportError:
    python_exe = sys.executable
    target = os.path.join(sys.prefix, 'lib', 'site-packages')
    
    subprocess.call([python_exe, '-m', 'ensurepip'])
    subprocess.call([python_exe, '-m', 'pip', 'install', '--upgrade', 'pip'])
    # install required packages
    subprocess.call([python_exe, '-m', 'pip', 'install', '--upgrade', 'notify-py', '-t', target])
    subprocess.call([python_exe, '-m', 'pip', 'install', '--upgrade', 'discord', '-t', target])
    subprocess.call([python_exe, '-m', 'pip', 'install', '--upgrade', 'aiohttp', '-t', target])
    subprocess.call([python_exe, '-m', 'pip', 'install', '--upgrade', 'asyncio', '-t', target])

os.system("cls")

def send_message_to_bot(message):
    host = '127.0.0.1'
    port = 65432

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall(message.encode())


DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1346076038387732480/50d-BremraDRbSfeHpvnbOYzpaFbhBskjEwj8uYj4u3sVDzwmH54XYHg5prAJpOMqhvy"

class RenderNotifier:
    def __init__(self):
        self.sound = True
        self.desktop = True
        self.discord_webhook = True
        self.webhook = True
        self.notified = False
        self.sound_path = ''
        self.blend_filepath = None
        self.blend_filename = None
        self.is_animation = False
        self.total_frames = 0
        self.avarage_est_frames = []
        self.FRAME_START_TIME = None
        self.RENDER_START_TIME = None
        self.RENDER_PRE_TIME = None
        self.RENDER_TOTAL_TIME = None
        self.RENDER_FRIST_FRAME = None
        self.RENDER_CURRENT_FRAME = None
        self.RENDER_CANCELLED_TIME = None
        self.estimation = ""
        self.total_frames = 0
        self.total_rendered = ""
        self.total_to_render = ""
        self.total_render_time = ""
        self.avarage_time = 0
        self.job_type = ""
        self.blender_data = {}
        self.current_frame = None
        self.counter = 0
        self.precountdown = 0.0
        self.webhook_url = DISCORD_WEBHOOK_URL
        self.message_id = None
        
        self.file = None
        self.no_preview = False
        self.rendered_frame_path = ""
        self.first_rendered_frame_path = ""
        
        self.tmp_save = "C:/tmp/"
        
        self.embed = Embed(title="🎬 Blender Render Status", description="Initializing...", colour=0x3498db)
                
        self.still_embed = discord.Embed(type="rich", color=discord.Color.gold())

        self.animation_embed = discord.Embed(type="rich", color=discord.Color.gold())

        self.end = False
        # Start an asyncio event loop in a separate thread
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.run_async_loop, daemon=True).start()
    
    def clean_var(self):
        self.is_animation = False
        self.total_frames = 0
        self.avarage_est_frames = []
        self.FRAME_START_TIME = None
        self.RENDER_START_TIME = None
        self.RENDER_PRE_TIME = None
        self.RENDER_TOTAL_TIME = None
        self.RENDER_FRIST_FRAME = None
        self.RENDER_CURRENT_FRAME = None
        self.RENDER_CANCELLED_TIME = None
        self.estimation = ""
        self.total_frames = 0
        self.total_rendered = ""
        self.total_to_render = ""
        self.total_render_time = ""
        self.avarage_time = 0
        self.job_type = ""
        self.blender_data = {}
        self.current_frame = None
        self.counter = 0
        self.precountdown = 0.0
    
    def notifi_desktop(scene,*args):
        print("\n Notifing via desktop \n")
        notification = Notify()
        notification.title = "Render complete"
        notification.message = "Your Blender render is complete"
        notification.send()

    
    def run_async_loop(self):
        """Runs the asyncio event loop in a separate thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        if self.end:
            self.loop.stop()
    
    #send message or edit embeded message
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
        

        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(self.webhook_url, session=session)
            if self.message_id:
                try:
                    if self.blender_data['job_type'] == "Aniamtion": 
                        try:
                            if finished:
                                await webhook.edit_message(self.message_id, embed=self.animation_embed,attachments=[self.file,self.thumbfile])
                            elif canceled:
                                await webhook.edit_message(self.message_id, embed=self.animation_embed,attachments=[self.file,self.thumbfile])
                            elif self.blender_data["frames_rednered"] == 1:
                                await webhook.edit_message(self.message_id, embed=self.animation_embed,attachments=[self.file])
                            else:
                                await webhook.edit_message(self.message_id, embed=self.animation_embed)
                        except:
                            self.animation_embed.description+= "\n image too large for preview"
                            if finished:
                                await webhook.edit_message(self.message_id, embed=self.animation_embed)
                            elif canceled:
                                await webhook.edit_message(self.message_id, embed=self.animation_embed)
                            elif self.blender_data["frames_rednered"] == 1:
                                await webhook.edit_message(self.message_id, embed=self.animation_embed)
                            else:
                                await webhook.edit_message(self.message_id, embed=self.animation_embed)
                    else:
                        try:
                            if finished:
                                await webhook.edit_message(self.message_id, embed=self.still_embed,attachments=[self.file])
                            elif canceled:
                                await webhook.edit_message(self.message_id, embed=self.still_embed,attachments=[self.file])
                            else:
                                await webhook.edit_message(self.message_id, embed=self.still_embed)
                        except:
                            self.still_embed.description+= "\n image too large for preview"
                            if finished:
                                await webhook.edit_message(self.message_id, embed=self.still_embed)
                            elif canceled:
                                await webhook.edit_message(self.message_id, embed=self.still_embed)
                            else:
                                await webhook.edit_message(self.message_id, embed=self.still_embed)
                        
                    if canceled or finished:
                        #self.animation_embed.clear_fields()
                        #self.still_embed.clear_fields()
                        self.message_id = None
                        
                except Exception as e:
                    print(f"⚠️ Error updating message: {e}")
            else:
                if self.blender_data['job_type'] == "Aniamtion": 
                    msg = await webhook.send(embed=self.animation_embed, username="Blender Bot", wait=True)
                    self.message_id = msg.id
                else:
                    msg = await webhook.send(embed=self.still_embed, username="Blender Bot", wait=True)
                    self.message_id = msg.id
    
    def send_webhook_non_blocking(self, init=False, frame=False, finished=False, canceled=False):
        """Schedule webhook execution using a separate thread-safe event loop."""
        future = asyncio.run_coroutine_threadsafe(
            self.send_or_update_embed(init, frame, finished, canceled),
            self.loop
        )
        future.result()  # Ensure the coroutine executes correctly

    #load data into embeds
    def em_init(self,isAniamtion):
        
        #global blender, render_embed
        self.animation_embed = Embed(title=self.blender_data['project_name'], description="Starting render job..", colour=discord.Colour.blue())
        self.still_embed = Embed(title=self.blender_data['project_name'], description="Starting render job..", colour=discord.Colour.gold())
        
        print("Starting")
        #while len(render_embed.fields) <= 9:
        #    render_embed.add_field(name="\u200b", value="\u200b", inline=False)  # Adds empty fields
        #render_embed = self.msg.embeds[0]    
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
        else: 
            self.still_embed.add_field(name="Job type", value=self.blender_data['job_type'], inline=True)
            self.still_embed.add_field(name="Frame", value=self.blender_data['frame'], inline=True)
            self.still_embed.add_field(name="Total time elapsed", value="...", inline=False)
            self.still_embed.set_footer(text="*(^◕.◕^)*")
       
    def em_post(self,isAniamtion):
        
        print("\nrendering")    
        print(f"Current fields complere: {self.animation_embed.fields}")

        print(f"Trying to set field at index 3 with frame: {self.blender_data['frame']}")

        if isAniamtion: 
            print(self.blender_data["frames_rednered"])
            if self.blender_data["frames_rednered"] == 1:
                self.file=discord.File(self.blender_data['first_render_filepath'],filename="first_render.png")
                atach = "attachment://first_render.png"
                print(atach)
                self.animation_embed.set_thumbnail(url=atach)
                
                self.animation_embed.description += "\nFrist frame rendered"
                self.animation_embed.set_field_at(index=3,name="Frame", value=self.blender_data['frame'], inline=False)
                self.animation_embed.set_field_at(index=4,name="frames rendered", value="("+str(self.blender_data['frames_rednered'])+"/"+str(self.blender_data['total_frames'])+")", inline=True)
                self.animation_embed.set_field_at(index=5,name="Frame time", value=self.blender_data['RENDER_FRIST_FRAME'], inline=True)
                self.animation_embed.set_field_at(index=6,name="Est. next frame", value=self.blender_data['next_frame_countdown'], inline=True)
                self.animation_embed.set_field_at(index=8,name="Est. render job" + self.blender_data['countdown'], value=self.blender_data['est_render_job'], inline=False)
                self.animation_embed.colour=discord.Colour.gold()
                
                self.animation_embed.set_footer(text= "(。>︿<)_θ")
            else:
                self.animation_embed.set_field_at(index=3,name="Frame", value=self.blender_data['frame'], inline=False)
                self.animation_embed.set_field_at(index=4,name="frames rendered", value="("+str(self.blender_data['frames_rednered'])+"/"+str(self.blender_data['total_frames'])+")", inline=True)
                self.animation_embed.set_field_at(index=5,name="Frame time", value=self.blender_data['RENDER_CURRENT_FRAME'], inline=True)
                self.animation_embed.set_field_at(index=6,name="Est. next frame", value=self.blender_data['next_frame_countdown'], inline=True)
                self.animation_embed.set_field_at(index=7,name="Avarage per frame", value=f"{self.blender_data['avarage_time']}", inline=True)
                self.animation_embed.set_field_at(index=8,name="Est. render job" + self.blender_data['countdown'], value=self.blender_data['est_render_job'], inline=False)
        
    def em_complete(self,isAniamtion):
        
        print("\ncompleting render job")
        if isAniamtion: 
            try:
                print(f"Current fields complere: {self.animation_embed.fields}")
                self.file=discord.File(self.blender_data['render_filepath'],filename="complete_render.png")
                atach = "attachment://complete_render.png"
                self.thumbfile=discord.File(self.blender_data['first_render_filepath'],filename="first_render.png")
                thumbatach = "attachment://first_render.png"
                self.animation_embed.set_thumbnail(url=thumbatach)

                print(atach)
                self.animation_embed.set_image(url=atach)
                self.animation_embed.description += "\nRender complete"
                self.animation_embed.set_field_at(index=7, name="Avarage per frame", value=self.blender_data['avarage_time'], inline=True)
                self.animation_embed.set_field_at(index=9, name="Total est. time", value=self.blender_data['total_Est_time'], inline=True)
                self.animation_embed.set_field_at(index=10, name="Total time elapsed", value=self.blender_data['total_time_elapsed'], inline=True)
                self.animation_embed.set_footer(text="( *︾▽︾)")
                self.animation_embed.colour=discord.Colour.green()
            except Exception as e:
                print(f"An error occurred: {e}")
        else:
            try:
                self.file=discord.File(self.blender_data['render_filepath'],filename="render.png")
                atach = "attachment://render.png"
                print(atach)
                self.still_embed.set_image(url=atach)
                self.still_embed.description += "\nRender complete"
                self.still_embed.set_field_at(index=2, name="Total time elapsed", value=self.blender_data['total_time_elapsed'], inline=False)
                self.still_embed.colour=discord.Colour.green()
                self.animation_embed.set_footer(text="( *︾▽︾)")
            except Exception as e:
                print(f"An error occurred in complete: {e}")    
                
    def em_cancel(self,isAniamtion):
        
        print("Starting")
            
        if isAniamtion: 
            try:
                if self.blender_data["frames_rednered"] > 1:
                    self.thumbfile=discord.File(self.blender_data['first_render_filepath'],filename="first_render.png")
                    thumbatach = "attachment://first_render.png"
                    self.animation_embed.set_thumbnail(url=thumbatach)
                
                self.file=discord.File(self.blender_data['render_filepath'],filename="cencel_render.png")
                atach = "attachment://cencel_render.png"
                print(atach)
                self.animation_embed.set_image(url=atach)
                self.animation_embed.description += "\nCanceled"
                self.animation_embed.set_field_at(index=3,name="Frame", value=self.blender_data['current_frame'], inline=True)
                self.animation_embed.add_field(name="Still to render", value="("+str(self.blender_data['frames_still_to_render'])+"/"+str(self.blender_data['total_frames'])+")", inline=False)
                self.animation_embed.add_field(name="Job Cancelled", value=self.blender_data['RENDER_CANCELLED_TIME'], inline=False)
                self.animation_embed.set_footer(text="[X_ X)")
                self.animation_embed.colour=discord.Colour.red()
            except Exception as e:
                print(f"An error occurred in cancel: {e}")  
        else:
            self.file=discord.File(self.blender_data['render_filepath'],filename="cencel_render.png")
            atach = "attachment://cencel_render.png"
            print(atach)
            self.still_embed.set_image(url=atach)
            self.still_embed.add_field(name="Job Cancelled", value=str(self.blender_data['RENDER_CANCELLED_TIME']), inline=False)
            self.still_embed.set_footer(text="[X_ X)")
            self.still_embed.colour=discord.Colour.red()


    #handle render logic
    def render_init(self,scene,*args):
        self.clean_var()
        #get blend file name
        self.blend_filepath = bpy.data.filepath
        self.blend_filename = os.path.basename(self.blend_filepath) if self.blend_filepath else "Untitled.blend"
        self.blend_filename = self.blend_filename[:-6]
        
        self.RENDER_START_TIME = datetime.now()
        self.render_start_countdown = time.time()
        self.total_frames = bpy.context.scene.frame_end - bpy.context.scene.frame_start + 1
        
        self.blender_data["call_type"] = "render_init"
        self.blender_data["project_name"] = self.blend_filename
        self.blender_data["total_frames"] = self.total_frames
        
        print("\nStarting Render\n")
        print(bpy.context.scene.frame_current)
            
        print(self.blender_data)

    def render_pre(self,scene,*args):
        self.current_frame = bpy.context.scene.frame_current
        self.blender_data["frame"] = bpy.context.scene.frame_current
        print(self.current_frame)
        if self.current_frame == bpy.context.scene.frame_start:
            self.is_animation = True
            self.job_type = "Aniamtion"  
            self.blender_data["job_type"] = self.job_type
            self.blender_data["frame"] = self.current_frame
            self.blender_data["frame_range"] = f"{bpy.context.scene.frame_start} - {bpy.context.scene.frame_end}"
            self.blender_data["Total_frames_to_render"] = self.total_frames
            #send_message_to_bot(blender_data)
            self.send_webhook_non_blocking(init=True)
            #asyncio.run(Blender_hook(self.blender_data,True))
        
        elif self.current_frame != bpy.context.scene.frame_start and self.is_animation == False:
            #is_animation = False
            self.job_type = "Still"
            self.blender_data["job_type"] = self.job_type
            self.blender_data["frame"] = self.current_frame
            #send_message_to_bot(blender_data)
            self.send_webhook_non_blocking(init=True)
            #asyncio.run(Blender_hook(self.blender_data,True))
            
    def render_post(self,scene,*args):
        self.blender_data["call_type"] = "render_post"
        
        self.current_frame = bpy.context.scene.frame_current
        
        if self.is_animation:
            #checks if the current frame is the first frame
            print(self.current_frame == bpy.context.scene.frame_start)
            if self.current_frame == bpy.context.scene.frame_start:
                print("its the frist frame")
                self.RENDER_FRIST_FRAME = datetime.now() - self.RENDER_START_TIME
                self.precountdown = time.time() - self.render_start_countdown
                self.countdown = int(time.time() + self.precountdown * (self.total_frames - self.counter))
                self.current_countdown = int(time.time() + self.precountdown)
                self.precountdown = time.time()
                print(self.RENDER_FRIST_FRAME.seconds)
                self.avarage_est_frames.append(self.RENDER_FRIST_FRAME)
                self.RENDER_PRE_TIME = datetime.now()
                self.counter += 1
                
                self.first_rendered_frame_path = bpy.path.abspath(scene.render.frame_path())
                scene = bpy.context.scene
                render = scene.render
                is_movie_format = render.is_movie_format
                if is_movie_format == False and bpy.context.scene.render.file_extension == ".png":
                    file_extension = bpy.context.scene.render.file_extension
                else:
                    self.no_preview = True
                
                if not self.no_preview:
                    first_filename = os.path.basename(self.first_rendered_frame_path)
                    
                    print(first_filename)
                    self.blender_data["first_render_filepath"] = self.first_rendered_frame_path
                    self.blender_data["first_filename"] = first_filename
                
                self.blender_data["RENDER_FRIST_FRAME"] = str(self.RENDER_FRIST_FRAME)[:-4]
                self.blender_data["est_render_job"] = str(self.RENDER_FRIST_FRAME * (self.total_frames - self.counter))[:-4]
                self.blender_data["frames_left"] = f"{self.total_frames - self.counter}"
                self.blender_data["frames_rednered"] = self.counter
                self.blender_data["countdown"] = f"<t:{self.countdown}:R>"
                self.blender_data["next_frame_countdown"] = f"<t:{self.current_countdown}:R>"
                
                print(self.blender_data)
                
            
                #send_message_to_bot(blender_data)
            else:
                try:
                    print("its not the frist frame")
                    self.precountdown = time.time() - self.precountdown
                    self.countdown = int(time.time() + self.precountdown * (self.total_frames - self.counter))
                    self.current_countdown = int(time.time() + self.precountdown)
                    self.counter += 1
                    self.RENDER_CURRENT_FRAME = datetime.now() - self.RENDER_PRE_TIME
                    self.avarage_est_frames.append(self.RENDER_CURRENT_FRAME) 
                    self.RENDER_PRE_TIME = datetime.now()
                    self.precountdown = time.time()
                    
                    if self.total_frames != self.counter:
                        self.blender_data["est_render_job"] = str(self.RENDER_CURRENT_FRAME * (self.total_frames - self.counter))[:-4]
                    else:
                        self.blender_data["est_render_job"] = str(self.RENDER_CURRENT_FRAME * (self.total_frames - self.counter + 1))[:-4]
                    self.blender_data["frame"] = bpy.context.scene.frame_current
                    self.blender_data["RENDER_CURRENT_FRAME"] = str(self.RENDER_CURRENT_FRAME)[:-4]
                    self.blender_data["frames_left"] = f"{self.total_frames - self.counter}"
                    self.blender_data["frames_rednered"] = self.counter
                    self.blender_data["countdown"] = f"<t:{self.countdown}:R>"
                    self.blender_data["next_frame_countdown"] = f"<t:{self.current_countdown}:R>"

                except Exception as e:
                    print(e)
                    print("its a still render job")
            
            print(self.RENDER_FRIST_FRAME)
            
            print(self.avarage_est_frames)
            print(len(self.avarage_est_frames))
            
            avg = datetime.now() - datetime.now()
            for est in self.avarage_est_frames:
                avg += est / len(self.avarage_est_frames)
            frame = scene.frame_current
            
            self.avarage_time = avg
            self.blender_data["avarage_time"] = str(self.avarage_time)[:-4]
            #send_message_to_bot(blender_data)
            self.send_webhook_non_blocking(frame=True)
            #asyncio.run(Blender_hook(blender_data))
            print(self.blender_data)
            
            print(self.avarage_time)

    def on_frame_render(self,scene, *args):
        
        if self.current_frame == bpy.context.scene.frame_start:
            None
        else:
            self.rendered_frame_path = bpy.path.abspath(scene.render.frame_path())

        print(f"Frame saved at: {self.rendered_frame_path}")
    
    def complete(self,scene,*args):
        self.RENDER_TOTAL_TIME = datetime.now() - self.RENDER_START_TIME
        self.blender_data["call_type"] = "complete"
        scene = bpy.context.scene
        render = scene.render
        print(self.tmp_save)
        is_movie_format = render.is_movie_format
        if is_movie_format == False and bpy.context.scene.render.file_extension == ".png":
            file_extension = bpy.context.scene.render.file_extension
        else:
            self.no_preview = True
        
        if self.is_animation:
            
            if not self.no_preview:
                filename = os.path.basename(self.rendered_frame_path)
                
                print(filename)
                self.blender_data["render_filepath"] = self.rendered_frame_path
                self.blender_data["render_filename"] = filename
            self.blender_data["avarage_time"] = str(self.avarage_time)[:-4]
            self.blender_data["total_Est_time"] = str(self.RENDER_FRIST_FRAME * self.total_frames)[:-4]
            self.blender_data["total_time_elapsed"] = str(self.RENDER_TOTAL_TIME)[:-4]
            
            #send_message_to_bot(blender_data)
            #asyncio.run.Blender_hook(blender_data)
        else:
            if not self.no_preview:
                render_path = render.filepath
                print(render_path)
                image = bpy.data.images['Render Result']
                
                if not is_movie_format:
                    render_path += file_extension  # Default to PNG if no extension
                    filename = os.path.basename(render_path)
                    image.save_render(self.tmp_save+filename)
                    
                print(filename)
                self.blender_data["render_filepath"] = self.tmp_save+filename
                self.blender_data["render_filename"] = filename
            self.blender_data["total_time_elapsed"] = str(self.RENDER_TOTAL_TIME)[:-4]
            #send_message_to_bot(blender_data)
        
        self.send_webhook_non_blocking(finished=True)
        #asyncio.run(Blender_hook(blender_data))
        
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

    def cancel(self,scene,*args):
        self.RENDER_CANCELLED_TIME = datetime.now() - self.RENDER_START_TIME
        
        cancel_frame = self.current_frame #bpy.context.scene.frame_current
        self.blender_data["call_type"] = "cancel"
        
        scene = bpy.context.scene
        render = scene.render
        print(self.tmp_save)
        is_movie_format = render.is_movie_format
        if is_movie_format == False and bpy.context.scene.render.file_extension == ".png":
            file_extension = bpy.context.scene.render.file_extension
        else:
            self.no_preview = True
        
        if self.is_animation:
            render_path = render.filepath
            print(render_path)
            image = bpy.data.images['Render Result']
            
            
            if not is_movie_format:
                render_path += file_extension  # Default to PNG if no extension
                filename = os.path.basename(render_path)
                try:
                    image.save_render(self.tmp_save+filename)
                except Exception as e:
                    print(f"error while saving image: {e}")
                    self.animation_embed.description += "\nno priview could be saved"
                
            print(filename)
            self.blender_data["render_filepath"] = self.tmp_save+filename
            self.blender_data["render_filename"] = filename
            self.blender_data["current_frame"] = cancel_frame
            self.blender_data["total_frames_rendered"] = bpy.context.scene.frame_end - cancel_frame
            self.blender_data["frames_still_to_render_range"] = f"{cancel_frame} - {bpy.context.scene.frame_end}"
            self.blender_data["frames_still_to_render"] = f"{bpy.context.scene.frame_end - self.current_frame}"
            self.blender_data["RENDER_CANCELLED_TIME"] = str(self.RENDER_CANCELLED_TIME)[:-4]
            
        else:
            render_path = render.filepath
            print(render_path)
            image = bpy.data.images['Render Result']
            
            if not is_movie_format:
                render_path += file_extension  # Default to PNG if no extension
                filename = os.path.basename(render_path)
                image.save_render(self.tmp_save+filename)
                
            print(filename)
            self.blender_data["render_filepath"] = self.tmp_save+filename
            self.blender_data["render_filename"] = filename
            self.blender_data["RENDER_CANCELLED_TIME"] = str(self.RENDER_CANCELLED_TIME)[:-4]
            
        
        self.send_webhook_non_blocking(canceled=True)
        #send_message_to_bot(blender_data)
        #asyncio.run(Blender_hook(blender_data))
            
        print("Render Canceled After:", self.RENDER_CANCELLED_TIME)
        print(self.blender_data)


    #send json payload via webhook
    def send_webhook(self,scene,*args):
        #self.WEBHOOK_URL = "http://127.0.0.1:5000/webhookcallback" #webhook to flask test server
        self.WEBHOOK_URL = "https://mosakohome.duckdns.org:8123/api/webhook/-blender3XsCcti0V19vzX-" #homeassistant
        #payload = json.dumps(self.blender_data, indent=4)
        payload = self.blender_data
        print(payload)
        response = requests.post(self.WEBHOOK_URL, json=payload)
        
        r = requests.post(self.WEBHOOK_URL)
        
        if response.status_code == 200:
            print('Webhook sent successfully!')
            print(r)
        else:
            print(f'Failed to send webhook. Status code: {response.status_code}')
            print(response.text)
        
def send_message_to_bot(message):
    host = '127.0.0.1'
    port = 65432

    data = json.dumps(str(message))
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall(bytes(data,encoding=("utf-8")))
    

notifier = RenderNotifier()

#@persistent

def register():
    bpy.app.handlers.render_init.append(notifier.render_init)
    bpy.app.handlers.render_post.append(notifier.render_post)
    bpy.app.handlers.render_post.append(notifier.send_webhook)
    bpy.app.handlers.render_pre.append(notifier.render_pre)
    bpy.app.handlers.render_pre.append(notifier.send_webhook)
    bpy.app.handlers.render_complete.append(notifier.complete)
    bpy.app.handlers.render_complete.append(notifier.notifi_desktop)
    bpy.app.handlers.render_complete.append(notifier.send_webhook)
    bpy.app.handlers.render_cancel.append(notifier.cancel)
    bpy.app.handlers.render_cancel.append(notifier.send_webhook)
    bpy.app.handlers.render_write.append(notifier.on_frame_render)
    
def unregister():
    bpy.app.handlers.render_init.remove(notifier.render_init)
    bpy.app.handlers.render_complete.remove(notifier.complete)
    bpy.app.handlers.render_cancel.remove(notifier.cancel)
    bpy.app.handlers.render_complete.remove(notifier.notifi_desktop)


register()