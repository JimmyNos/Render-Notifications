import ast
from datetime import datetime
import json
import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import socket

class Client(commands.Bot):
    async def on_ready(self):
        print(f"Logged on as {self.user}!")
        self.channel = await self.fetch_channel(1344591600332050473)
        await self.change_presence(status=discord.Status.idle)
        #await auto_send(channel)
        self.loop.create_task(self.start_socket_server())
        
        try:
            guild = discord.Object(id=1247011455304339537)
            synced = await self.tree.sync(guild = guild)
            print(f"Synced {len(synced)} commands to guild {guild.id}!")
        except Exception as e:
            print(f"Error syncing commands: {e}")
            
    async def start_socket_server(self):
        server = await asyncio.start_server(self.handle_client, '127.0.0.1', 65432)
        async with server:
            await server.serve_forever()
    
    blender = {}
    embed1 = None
    msg = None
    render_embed = discord.Embed(type="rich", color=discord.Color.green())
        
            
    async def handle_client(self, reader, writer):
        global blender, msg #, render_embed
        data = await reader.read(2000)
        message = data.decode()
        blender = ast.literal_eval(json.loads(message))
        
        print(type(blender)) 
        
        print(blender) 
        
        await self.change_presence(status=discord.Status.online,activity=discord.Activity(type=5, name=f"{blender['project_name']}"))
        
        self.render_embed.title=blender['project_name']
        self.render_embed.description="Starting render job.."
        self.render_embed.set_author(name=" ",icon_url="https://public.blenderkit.com/thumbnails/assets/e44883e908f343b184f5b520531891f3/files/thumbnail_3c29b5df-fba5-4a67-807f-03931ceace40.png.2048x2048_q85.png")
    
        #self.render_embed.add_field(name="test", value=blender['job_type'], inline=True)
        print(len(self.render_embed.fields))    
        print(blender['call_type'])
        print(blender['job_type'])
        if blender['call_type'] == "render_init":
            if blender['job_type'] == "Aniamtion": 
                self.render_init(True)
            else: 
                self.render_init(False)
            print(len(self.render_embed.fields))    
            if self.channel:
                self.msg = await self.channel.send(embed=self.render_embed)
                
            writer.close()
            
        elif blender['call_type'] == "render_post":
            if blender['job_type'] == "Aniamtion": 
                self.render_post(True)
            else: 
                self.render_post(False)
            
            if self.channel:
                await self.msg.edit(embed=self.render_embed)
            writer.close()
            
        elif blender['call_type'] == "complete":
            if blender['job_type'] == "Aniamtion": 
                self.complete(True)
                print("animation finishing...")
            else: 
                self.complete(False)
            
            if self.channel:
                await self.msg.edit(embed=self.render_embed)
                self.render_embed.clear_fields()
            writer.close()
            
        elif blender['call_type'] == "cancel":
            if blender['job_type'] == "Aniamtion": 
                self.cancel(True)
            else: 
                self.cancel(False)
            
            if self.channel:
                await self.msg.edit(embed=self.render_embed)
                self.render_embed.clear_fields()
            writer.close()
            
        writer.close()
    
    def render_init(self,isAniamtion):
        #global blender, render_embed
        
        print("Starting")
        print(len(self.render_embed.fields))
        #while len(render_embed.fields) <= 9:
        #    render_embed.add_field(name="\u200b", value="\u200b", inline=False)  # Adds empty fields
        #render_embed = self.msg.embeds[0]    
        if isAniamtion: 
            self.render_embed.add_field(name="Job type", value=blender['job_type'], inline=False)
            self.render_embed.add_field(name="Total frames", value=blender['total_frames'], inline=True)
            self.render_embed.add_field(name="Frame Range", value=blender['frame_range'], inline=True)
            self.render_embed.add_field(name="Frame", value=blender['frame'], inline=True)
            self.render_embed.add_field(name="frames rendered", value="...", inline=True)
            self.render_embed.add_field(name="Frame time", value="...", inline=True)
            self.render_embed.add_field(name="Est. next frame", value="...", inline=True)
            self.render_embed.add_field(name="Avarage per frame", value="...", inline=False)
            self.render_embed.add_field(name="Est. render job", value="...", inline=True)
            self.render_embed.add_field(name="Total est. time", value="...", inline=True)
            self.render_embed.add_field(name="Total time elapsed", value="...", inline=True)
            self.render_embed.set_footer(text="*(^◕.◕^)*")
            #self.render_embed.set_field_at(index=3,name="Frame edit", value=blender['frame'], inline=False)
        else: 
            self.render_embed.add_field(name="Job type", value=blender['job_type'], inline=True)
            self.render_embed.add_field(name="Frame", value=blender['frame'], inline=True)
            self.render_embed.add_field(name="Total time elapsed", value="...", inline=False)
            self.render_embed.set_footer(text="*(^◕.◕^)*")
        
        print(len(self.render_embed.fields))    
              
    def render_post(self,isAniamtion):
        #global blender,render_embed
        
        print("\nrendering")
        print(len(self.render_embed.fields))    
        
        #render_embed = self.msg.embeds[0]
        if isAniamtion: 
            
            if blender["frames_rednered"] == 1:
                self.render_embed.description += "\nFrist frame rendered"
                self.render_embed.set_field_at(index=3,name="Frame", value=blender['frame'], inline=False)
                self.render_embed.set_field_at(index=4,name="frames rendered", value="("+str(blender['frames_rednered'])+"/"+str(blender['total_frames'])+")", inline=True)
                self.render_embed.set_field_at(index=5,name="Frame time", value=blender['RENDER_FRIST_FRAME'], inline=True)
                self.render_embed.set_field_at(index=6,name="Est. next frame", value=blender['next_frame_countdown'], inline=True)
                self.render_embed.set_field_at(index=8,name="Est. render job" + blender['countdown'], value=blender['est_render_job'], inline=False)
                
                self.render_embed.set_footer(text= "(。>︿<)_θ")

            else:
                self.render_embed.description += "\nrendering.."
                self.render_embed.set_field_at(index=3,name="Frame", value=blender['frame'], inline=False)
                self.render_embed.set_field_at(index=4,name="frames rendered", value="("+str(blender['frames_rednered'])+"/"+str(blender['total_frames'])+")", inline=True)
                self.render_embed.set_field_at(index=5,name="Frame time", value=blender['RENDER_CURRENT_FRAME'], inline=True)
                self.render_embed.set_field_at(index=6,name="Est. next frame", value=blender['next_frame_countdown'], inline=True)
                self.render_embed.set_field_at(index=7,name="Avarage per frame", value=f"{blender['avarage_time']}", inline=True)
                self.render_embed.set_field_at(index=8,name="Est. render job" + blender['countdown'], value=blender['est_render_job'], inline=False)
        
        print(len(self.render_embed.fields))    

    def complete(self,isAniamtion):
        #global blender,render_embed
        
        print("\ncompleting render job")
        print(len(self.render_embed.fields))
        
        if isAniamtion: 
            try:
                self.render_embed.description += "\nRender complete"
                self.render_embed.set_field_at(index=7, name="Avarage per frame", value=blender['avarage_time'], inline=True)
                self.render_embed.set_field_at(index=9, name="Total est. time", value=blender['total_Est_time'], inline=True)
                self.render_embed.set_field_at(index=10, name="Total time elapsed", value=blender['total_time_elapsed'], inline=True)
                self.render_embed.set_footer(text="( *︾▽︾)")
            except Exception as e:
                print(f"An error occurred: {e}")
        else:
            try:
                self.render_embed.description += "\nRender complete"
                self.render_embed.set_field_at(index=2, name="Total time elapsed", value=blender['total_time_elapsed'], inline=False)
            except Exception as e:
                print(f"An error occurred in complete: {e}")    
                
    def cancel(self,isAniamtion):
        #global blender,render_embed
        
        print("Starting")
            
        if isAniamtion: 
            try:
                self.render_embed.description += "\nCannceled"
                self.render_embed.set_field_at(index=3,name="Frame", value=blender['current_frame'], inline=True)
                self.render_embed.add_field(name="Still to render", value=blender['frames_still_to_render'], inline=False)
                self.render_embed.add_field(name="Job Cancelled", value="("+str(blender['RENDER_CANCELLED_TIME'])+"/"+str(blender['total_frames'])+")", inline=False)
                self.render_embed.set_footer(text="[X_ X)")
            except Exception as e:
                print(f"An error occurred in cancel: {e}")  
        else:
            self.render_embed.add_field(name="Job Cancelled", value=str(blender['RENDER_CANCELLED_TIME']), inline=False)
            self.render_embed.set_footer(text="[X_ X)")
            
        
        
        
    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content.startswith("hello"):
            await message.channel.send(f"Hi {message.author}")

    async def on_reaction_add(self, reaction, user):
        await reaction.message.channel.send(f"{user} reacted with {reaction.emoji}")


intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="!", intents=intents)

#@tasks.loop(seconds=120)
async def auto_send(channel : discord.TextChannel):
    await channel.send(f"Test message every 120 seconds")


GUILD_ID = discord.Object(id=1247011455304339537)

@client.tree.command(name="hello", description="This is a test command",guild=GUILD_ID)
async def sayHello(interaction: discord.Integration):
    await interaction.response.send_message("Hello World")
    
@client.tree.command(name="echo", description="This is a repeat command",guild=GUILD_ID)
async def printer(interaction: discord.Integration, printer: str, num: int):
    response = ""
    for i in range(num):
        response += f"**{printer}**\n"
    await interaction.response.send_message(response)

embed = None
@client.tree.command(name="embed", description="embed demo!",guild=GUILD_ID)
async def myEmbed(interaction: discord.Integration):
    embed = discord.Embed(title="Title", url="https://youtu.be/xm3YgoEiEDc?si=4RLumVh6pSjwLBc_", description="*Alots* of **things** here <t:165132515:R>", color=discord.Color.gold())
    embed.set_thumbnail(url="https://ddz4ak4pa3d19.cloudfront.net/cache/6a/53/6a5314d57ccb486a5f71423783eda7f4.jpg")
    embed.add_field(name="Field 1 *title*", value="A work of art!", inline=False)
    embed.add_field(name="Field 2 title", value="Stuff *here* idk", inline=True)
    embed.add_field(name="Field 3 **title**", value="More stuff here too", inline=True)
    embed.add_field(name="Field 4 **title**", value="More stuff here too", inline=True)
    embed.add_field(name="Field 4 **title**", value="More stuff here too", inline=False)
    embed.add_field(name="Field 4 **title**", value="More stuff here too", inline=True)
    embed.add_field(name="Field 4 **title**", value="More stuff here too", inline=True)
    embed.add_field(name="Field 4 **title**", value="More stuff here too", inline=True)
    embed.add_field(name="Field 4 **title**", value="More stuff here too", inline=True)
    embed.set_footer(text="(^◕.◕^)*khkj*")
    embed.set_author(name=interaction.user.name, url="https://youtu.be/nV_awXI9XJY?si=pF3FjrhSamHIxJQz", icon_url="https://public.blenderkit.com/thumbnails/assets/e44883e908f343b184f5b520531891f3/files/thumbnail_3c29b5df-fba5-4a67-807f-03931ceace40.png.2048x2048_q85.png")
    ed = await client.channel.send(embed=embed) #interaction.response.send_message(embed=embed)
    embed.set_field_at(1,name="edit 1 title", value="Stuff *here* idk", inline=True)
    embed.set_field_at(4,name="edit 2 title", value="Stuff *here* idk", inline=True)
    embed.set_field_at(5,name="edit 2 title", value="Stuff *here* idk", inline=True)
    await ed.edit(embed=embed)
    
    

class View(discord.ui.View):
    @discord.ui.button(label="Button 1", style=discord.ButtonStyle.primary, emoji="👍")
    async def button_callback(self, button, interaction):
        await button.response.send_message("Button 1 pressed!")
    
    @discord.ui.button(label="Button 2", style=discord.ButtonStyle.red, emoji="👍")
    async def button_callback2(self, button, interaction):
        await button.response.send_message("Button 2 pressed!")
    
    @discord.ui.button(label="Button 3", style=discord.ButtonStyle.secondary, emoji="👍")
    async def button_callback3(self, button, interaction):
        await button.response.send_message("Button 3 pressed!")

@client.tree.command(name="buttons", description="show some buttons",guild=GUILD_ID)
async def myButtons(interaction: discord.Integration):
    await interaction.response.send_message(view=View())    
    
#client = Client(intents=intents)
client.run("MTM0NDU4MjAzMDMwMTU5MzYwMA.Gwofmn.Z4Vzv9f2B6nV95it72D0JKfJurdZLzT1IvqJUM")