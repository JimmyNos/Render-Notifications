import bpy

from bpy.types import Operator, AddonPreferences,PropertyGroup,Panel
from bpy.props import StringProperty, IntProperty, BoolProperty
from bpy.app.handlers import persistent

def update_third_party_webhook_every_frame(self, context):
    """Toggle all third-party webhook settings when 'notify on every frame' is toggled"""
    state = self.third_party_webhook_every_frame
    self.third_party_webhook_start = state
    self.third_party_webhook_first = state
    self.third_party_webhook_completion = state
    self.third_party_webhook_cancel = state

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
        name="Desktop notify with preview",
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
        description="Enable third-party third-party webhook notifications.",
        default=False
    )# type: ignore

class RenderNotificationsPanel:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

class RENDER_PT_Notifications(RenderNotificationsPanel, Panel):
    """Creates a notifications panel in the render properties tab"""
    bl_label = "Render Notifications"
    bl_idname = "RENDER_PT_Notifications"
    bl_order = 999
    
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
        props = scene.render_panel_props 
        layout.enabled = props.is_desktop
        
        # notification properties for desktop notifications
        desktop_box = layout.box()
        
        
        # If checkbox is enabled, show additional settings for desktop notifications
        
        desktop_col = desktop_box.column()
        desktop_col.label(text="Configure Notifications:")
        desktop_col.prop(props, "desktop_start", text="notify on start")
        desktop_col.prop(props, "desktop_first", text="notify on first")
        desktop_col.prop(props, "desktop_completion", text="notify on completion")
        desktop_col.prop(props, "desktop_cancel", text="notify on cancel")
            
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
        props = scene.render_panel_props 
        layout.enabled = props.is_discord
        
        # notification properties for discord notifications
        discord_box = layout.box()
        discord_col = discord_box.column()
        discord_col.label(text="Configure Notifications:")
        discord_col.prop(props, "discord_preview", text="Send previews")
        discord_col.prop(props, "use_custom_preview_path", text="Use custom preview path")
        discord_col.prop(props, "discord_preview_path", text="Previews save location") 

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
        props = scene.render_panel_props 
        layout.enabled = props.is_third_party_webhook
        
        # notification properties for webhook notifications
        third_party_webhook_box = layout.box()
        
        third_party_webhook_col = third_party_webhook_box.column()
        third_party_webhook_col.label(text="Configure Notifications:")
        third_party_webhook_col.prop(props, "third_party_webhook_every_frame", text="notify on every frame")
        third_party_webhook_col.prop(props, "third_party_webhook_start", text="notify on start")
        third_party_webhook_col.prop(props, "third_party_webhook_first", text="notify on first")
        third_party_webhook_col.prop(props, "third_party_webhook_completion", text="notify on completion")
        third_party_webhook_col.prop(props, "third_party_webhook_cancel", text="notify on cancel")

    
classes = [
    Render_Notifications_Properties, 
    RENDER_PT_Notifications,
    RENDER_PT_Desktop_Notifications,
    RENDER_PT_Discord_Notifications,
    RENDER_PT_Webhook_Notifications
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.render_panel_props = bpy.props.PointerProperty(type=Render_Notifications_Properties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    if hasattr(bpy.types.Scene, "render_panel_props"):
        del bpy.types.Scene.render_panel_props


if __name__ == "__main__":
    register()
