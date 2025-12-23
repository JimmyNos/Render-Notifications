import os
import sys
import json
import asyncio
import time
import aiohttp
from discord import Webhook, Embed
import discord

class DiscordProcessor:
    def __init__(self):
        # var
        self.init, self.frame, self.finished, self.canceled = False, False, False, False
        self.message_id = None
        self.discord_webhook_url = None
        self.blender_data = {}
        self.render_start_countdown = time.time()

    async def run(self):
        st_first = sys.stdin.readline().strip()
        try:
            try:
                data = json.loads(st_first)
            except json.JSONDecodeError:
                data = {"raw": st_first}

            response = {"received": data, "ack": True}
            print(json.dumps(response), flush=True)
        except Exception as e:
            print(f"Error processing initial line: {e}")
            
        self.blender_data = data
        self.discord_webhook_url = self.blender_data['discord_webhook_url']
                
                
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(self.discord_webhook_url, session=session)

            
            self.call_type()
            #await webhook.send(username="Blender Hook",content="test", wait=True)
            try:
                await self.send_or_update_embed(webhook, self.init, self.frame, self.finished, self.canceled)
            except Exception as e:
                print(f"Error sending or updating embed: {e}")
        
            # Loop reading JSON-lines from stdin and reply for each line.
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    data = {"raw": line}

                response = {"received": data, "ack": True}
                
                print(json.dumps(response), flush=True)

                # Allow the caller to request the child to exit
                if isinstance(data, dict) and data.get("cmd") == "exit":
                    break
                
                self.blender_data = data
                self.call_type()
                #await webhook.send(username="Blender Hook",content="test", wait=True)
                try:
                    await self.send_or_update_embed(webhook, self.init, self.frame, self.finished, self.canceled)
                except Exception as e:
                    print(f"Error sending or updating embed: {e}")
        
    def call_type(self):
        if self.blender_data['call_type'] == 'render_init':
            self.init = True
            self.frame = False
            self.finished = False
            self.canceled = False
        elif self.blender_data['call_type'] == 'render_post':
            self.init = False
            self.frame = True
            self.finished = False
            self.canceled = False
        elif self.blender_data['call_type'] == 'complete':
            self.init = False
            self.frame = False
            self.finished = True
            self.canceled = False
        elif self.blender_data['call_type'] == 'cancel':
            self.init = False
            self.frame = False
            self.finished = False
            self.canceled = True

    async def fetch_data(self, data):
        # Loop reading JSON-lines from stdin and reply for each line.
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                self.blender_data = json.loads(line)
            except json.JSONDecodeError:
                self.blender_data = {"raw": line}

            response = {"received": "data received. processing..", "ack": True}
            print(json.dumps(response), flush=True)
        
            # Allow the caller to request the child to exit
            if isinstance(self.blender_data, dict) and self.blender_data.get("cmd") == "exit":
                break
            
            await self.send_or_update_embed(self.webhook, self.init, self.frame, self.finished, self.canceled)

    # Load data into embeds
    def em_init(self,isAnimation):
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
        
        self.complete_embed = Embed(title="Render completed :white_check_mark:", 
                               description=f"Render job for {self.blender_data['project_name']} completed successfully!", 
                               colour=discord.Colour.light_embed(),
                               timestamp=discord.utils.utcnow())
        
        self.cancel_embed = Embed(title="Render canceled :x:", 
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
            self.animation_embed.add_field(name="Est. render job ", value="...", inline=True)
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
            if self.blender_data["isfirst_frame"]:
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
            
            self.frames_rendered_field = "("+str(self.blender_data['frames_rendered'])+"/"+str(self.blender_data['total_frames'])+") "+str(self.blender_data['rendered_frames_percentage'])+"%"
            
            #check if it's the first frame
            if self.blender_data["frames_rendered"] == 1:
                #print("First frame rendered")
                if self.blender_data["discord_preview"] and self.no_preview == False:
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
                self.animation_embed.set_field_at(index=4,name="frames rendered", value=self.frames_rendered_field, inline=True)
                self.animation_embed.set_field_at(index=5,name="Frame time", value=self.blender_data['RENDER_FIRST_FRAME'], inline=True)
                self.animation_embed.set_field_at(index=6,name="Est. next frame", value=self.blender_data['next_frame_countdown'], inline=True)
                self.animation_embed.set_field_at(index=8,name=f"Est. render job {self.blender_data['countdown']}", value=self.blender_data['est_render_job'], inline=False)
                self.animation_embed.colour=discord.Colour.gold()
                
                self.animation_embed.set_footer(text= "(。>︿<)_θ")
            else:
                self.animation_embed.set_field_at(index=3,name="Frame", value=self.blender_data['frame'], inline=False)
                self.animation_embed.set_field_at(index=4,name="frames rendered", value=self.frames_rendered_field, inline=True)
                self.animation_embed.set_field_at(index=5,name="Frame time", value=self.blender_data['RENDER_CURRENT_FRAME'], inline=True)
                self.animation_embed.set_field_at(index=6,name="Est. next frame", value=self.blender_data['next_frame_countdown'], inline=True)
                self.animation_embed.set_field_at(index=7,name="Avarage per frame", value=f"{self.blender_data['average_time']}", inline=True)
                self.animation_embed.set_field_at(index=8,name=f"Est. render job {self.blender_data['countdown']}", value=self.blender_data['est_render_job'], inline=False)
    
    # Load new data into embeds when the render job is complete  
    def em_complete(self,isAnimation):
        if isAnimation: 
            try:
                if self.blender_data["discord_preview"] and self.no_preview == False:
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
                
                if self.blender_data["discord_preview"] and self.no_preview == False:
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
                if self.blender_data["discord_preview"] and self.no_preview == False:
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
                    if self.blender_data["discord_preview"] and self.no_preview == False:
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
            if self.blender_data["discord_preview"] and self.no_preview == False:
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

    # Send a discord message when the render job is complete         
    async def send_on_complete(self, full_hook=None, webhook=None):
        #print(f"full_hook.guild_id: {full_hook.guild_id}, full_hook.channel_id: {full_hook.channel_id}, self.message_id: {self.message_id}")
        message_link = f"https://discord.com/channels/{full_hook.guild_id}/{full_hook.channel_id}/{self.message_id}"
        reply_content = f"{message_link}" # link to main message
        self.complete_embed.description += f"\n## {reply_content}"
        await webhook.send(username=self.blender_data["discord_webhook_name"], embed=self.complete_embed)
        #print("reply sent")
    
    # Send a discord message when the render job is canceled
    async def send_on_cancel(self, full_hook=None, webhook=None):
        #print(f"full_hook.guild_id: {full_hook.guild_id}, full_hook.channel_id: {full_hook.channel_id}, self.message_id: {self.message_id}")
        message_link = f"https://discord.com/channels/{full_hook.guild_id}/{full_hook.channel_id}/{self.message_id}"
        reply_content = f"{message_link}" # link to main message
        self.cancel_embed.description += f"\n## {reply_content}"
        await webhook.send(username=self.blender_data["discord_webhook_name"], embed=self.cancel_embed)
        #print("reply sent")
    
    # Send a new discord message or edit embeded message
    async def send_or_update_embed(self, webhook, init=False, frame=False, finished=False, canceled=False):
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
        if self.message_id:
            # If message_id is set, edit the existing message
            try:
                full_hook = await webhook.fetch()
                if self.blender_data['job_type'] == "Animation": 
                    # If the preview is enabled, send the embed with the preview images
                    if self.blender_data["discord_preview"]:
                        try:
                            await edit_animation(True)
                        except Exception as e:
                            # If the embed is too large or an error is cought, it try to send it without the image
                            print(f"Error occurred while embedding image in Discord webhook: {e}. This might be due to file size limitations or an invalid file path. (possiable fix: try reloading blender)")
                            self.animation_embed.description+= "\n Render too large for preview or failed to save."
                            await edit_animation()
                    else:
                        await edit_animation()
                else:
                    # Send still embed if the job is not an animation
                    if self.blender_data["discord_preview"]:
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
                msg = await webhook.send(embed=self.first_frame_embed, username=self.blender_data["discord_webhook_name"], wait=True)
                self.message_id = msg.id
                
            else:
                if self.blender_data["isfirst_frame"]:
                    msg = await webhook.send(embed=self.first_frame_embed, username=self.blender_data["discord_webhook_name"], wait=True)
                else:
                    msg = await webhook.send(embed=self.still_embed, username=self.blender_data["discord_webhook_name"], wait=True)
                self.message_id = msg.id
    

if __name__ == '__main__':
    asyncio.run(DiscordProcessor().run())