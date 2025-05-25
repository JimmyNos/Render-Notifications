
# Your Discord webhook URL
WEBHOOK_URL = "https://discord.com/api/webhooks/1346076038387732480/50d-BremraDRbSfeHpvnbOYzpaFbhBskjEwj8uYj4u3sVDzwmH54XYHg5prAJpOMqhvy"
import aiohttp
import asyncio
from discord import Webhook, Embed
import discord

async def run_webhook():
    webhook_url = WEBHOOK_URL
    #guild_id = "1247011455304339537"  # Replace with your actual server ID

    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(webhook_url, session=session)

        # Step 1: Send initial message
        original_message = await webhook.send(
            "This is the original message.",
            username="Webhook Bot",
            wait=True  # Important! Waits so we can edit it and get ID
        )

        # Step 2: Edit the original message
        await original_message.edit(content="This message has been edited.")

        # Step 3: Simulate a reply by linking to the original message
        channel_id = 1344591600332050473
        message_id = original_message.id
        full_hook = await webhook.fetch()
        
        

        message_link = f"https://discord.com/channels/{full_hook.guild_id}/{channel_id}/{1376296618789437511}"
        reply_content = f"{message_link}\nThis is a reply to the original."
        
        complete_embed = Embed(title="*Redner completed :checkered_flag: :white_check_mark: *", 
                               description=f"Render job for *incert* completed successfully!\n### {message_link}", 
                               colour=discord.Colour.light_embed(),
                               timestamp=discord.utils.utcnow())
        

        await webhook.send(username="Webhook Bot",embed=complete_embed)

# Run it
asyncio.run(run_webhook())
