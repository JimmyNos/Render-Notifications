# 🛎️ Render Notifications – Blender Add-on
**Render Notifications** is a Blender add-on that sends notifications when a render **starts**, **finishes**, or gets **canceled** using **Discord**, **desktop notifications**, or **webhooks** for custom platforms like **Home Assistant**.

Blender does not expose render progress or time directly to Python, so this add-on calculates the following after each frame:
- Render time
- Average time per frame
- Estimated total render time
- Frames remaining and percentage complete

---

## ✨ Features

### 🔔 🖥️ Desktop Notifications

  - Sends desktop notifications when a render:
    - Starts
    - Finishes
    - Gets canceled
    - Completes the first frame
  - Includes:
    - Time taken to render
    - Estimated total time for full render
  - Supports custom notification sounds (`.wav` format)
    
### 💬 Discord Webhook Integration

  - Sends a message to Discord when the render starts, and edits it as rendering progresses.
  - Supports preview images:
    - For single-frame renders: shows the final image
    - For animation jobs: shows the first and last frame
> ⚠️ **Note**: Previews rely on saving as `.png`. Formats like `.exr` are not supported for preview extraction.

### 🌐 Webhook Support
- Sends structured **JSON payloads** to your custom apps or third-party services (e.g. Home Assistant).
- Perfect for integrations with mobile alerts, dashboards, or automation workflows.

## 🧩 Installation
1. Download the latest version of the add-on as a `.zip` file.
2. In Blender, go to **Edit > Preferences > Add-ons**.
3. Click Install… and select the **.zip** file.
4. Enable the add-on from the list.

## 🔧 Configuration
Once enabled, the add-on panel will appear in the Render Properties tab.
###⚙️ Setup
1. Dependencies
   The add-on uses external Python libraries:
   - `notify-py`
   - `discord.py`
   - `aiohttp`
   If these are missing, they can be installed from within the Add-on Preferences.
2. After installing libraries
   Disable and re-enable the add-on to load the full settings interface.
3. Desktop Notifications
   - Enable the custom sound option (optional).
   - Attach your `.wav` file location.
4. Discord Webhook Settings
   - Set a **custom name** (optional).
   - Paste your **Discord webhook URL**.
     - Note: Get the Discord webhook via your channel settings.
   - You can define a **custom render preview save path**:
     - In either the **Preferences** or **Render Properties** tab.
     - If the path in Render Properties is invalid, the Preferences path will be used instead.
5. Webhook Notifications
   - Paste your **custom webhook URL** (e.g. for Home Assistant).
6. Render Properties Panel
   - You’ll find a new **Notifications** section.
   - Choose your notification options:
     - Desktop
     - Discord
       - Choose to send previews
     - Webhook
   - Choose when to be notified: Start, Cancel, First Frame, Completion

10. Paste your discord webhook url and the webhook url from your thrid-party application.
   - To set up the discord notifications, you will need to create a webhook for your discord channel and paste the url. You can setup a custom name or leave it blank to use the one setup in discord.
   - you can choose a cutom path for the render previews sent to discord in the prefrences or in the render prepertices. Note: if the location set in the render propertices is invalid, then the location set in prefrnces will take prioraty
11. Once setup in prefrences, you should see a 'Notifications section in the Render propertices'
   Here, you can choose your notification option and what to be notified on.

# Examples

### JSON payload examples
```
{
  "call_type": "complete",
  "project_name": "Untitled",
  "total_frames": 6,
  "frame": 115,
  "job_type": "Still",
  "total_time_elapsed": "0:00:00.69"
}
```

```
{
  "call_type": "render_init",
  "project_name": "Untitled",
  "total_frames": 6,
  "frame": 0,
  "job_type": "Animation",
  "frame_range": "0 - 5",
  "Total_frames_to_render": 6
}
```

```
{
  "call_type": "render_post",
  "project_name": "Untitled",
  "total_frames": 6,
  "frame": 4,
  "job_type": "Animation",
  "frame_range": "0 - 5",
  "Total_frames_to_render": 6,
  "RENDER_FIRST_FRAME": "0:00:01.05",
  "est_render_job": "0:00:00.75",
  "frames_left": "1",
  "frames_rendered": 5,
  "rendered_frames_percentage": 83.33,
  "countdown": "<t:1750442376:R>",
  "next_frame_countdown": "<t:1750442375:R>",
  "average_time": "0:00:00.80",
  "RENDER_CURRENT_FRAME": "0:00:00.75"
}
```

```
{
  "call_type": "complete",
  "project_name": "Untitled",
  "total_frames": 6,
  "frame": 5,
  "job_type": "Animation",
  "frame_range": "0 - 5",
  "Total_frames_to_render": 6,
  "RENDER_FIRST_FRAME": "0:00:01.05",
  "est_render_job": "0:00:00.74",
  "frames_left": "0",
  "frames_rendered": 6,
  "rendered_frames_percentage": 100.0,
  "countdown": "<t:1750442376:R>",
  "next_frame_countdown": "<t:1750442376:R>",
  "average_time": "0:00:00.79",
  "RENDER_CURRENT_FRAME": "0:00:00.74",
  "total_time_elapsed": "0:00:05.14",
  "total_Est_time": "0:00:06.30"
}
```

# 📜 License
This project is licensed under the GNU General Public License v3 (GPLv3).

# 🙋‍♂️ Author
Made with ☕ and 🧠 by Michael Mosako.
If you'd like to support the project, consider [buying me a coffee](https://buymeacoffee.com/jimmynostar).
