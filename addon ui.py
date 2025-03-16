import bpy # type: ignore

# Create a standalone property (not linked to anything)
class RenderPanelProperties(bpy.types.PropertyGroup):
    #desktop nitifications
    desktop_start: bpy.props.BoolProperty(
        name="Desktop notify on start",
        description="Recive desktop notifications when the render job starts.",
        default=False  # Starts unchecked
    ) # type: ignore
    desktop_first: bpy.props.BoolProperty(
        name="Desktop notify on first",
        description="Recive desktop notifications when the first frame has rendered.",
        default=False  # Starts unchecked
    )# type: ignore
    desktop_completion: bpy.props.BoolProperty(
        name="Desktop notify on completion",
        description="Recive desktop notifications when the render job is complete.",
        default=False  # Starts unchecked
    )# type: ignore
    desktop_cancel: bpy.props.BoolProperty(
        name="Desktop notify on cancel",
        description="Recive desktop notifications when the render job is canceled.",
        default=False  # Starts unchecked
    )# type: ignore
    
    
    #discord notifications
    discord_start: bpy.props.BoolProperty(
        name="Desktop notify on start",
        description="Recive discord notifications when the render job starts.",
        default=False  # Starts unchecked
    ) # type: ignore
    discord_first: bpy.props.BoolProperty(
        name="Desktop notify on first",
        description="Recive discord notifications when the first frame has rendered.",
        default=False  # Starts unchecked
    )# type: ignore
    discord_completion: bpy.props.BoolProperty(
        name="Desktop notify on completion",
        description="Recive discord notifications when the render job is complete.",
        default=False  # Starts unchecked
    )# type: ignore
    discord_cancel: bpy.props.BoolProperty(
        name="Desktop notify on cancel",
        description="Recive discord notifications when the render job is canceled.",
        default=False  # Starts unchecked
    )# type: ignore
    discord_preview: bpy.props.BoolProperty(
        name="Desktop notify with preview",
        description="Send the first and final frame to discord for an animation job, or a still image when a still render job is complete complete. Note: the default save location for the preview is set in the addon prefrences. if the size of the frame/still is larger than discord's allowed attachment size (with or without nitro), no preview will be sent.",
        default=False  # Starts unchecked
    )# type: ignore
    #discord_custom_tmp: bpy.props.BoolProperty(
    #    name="Custom tmp save path",
    #    description="Enable use custom tmp save path for preview frame for discord's embed message. Note: if the size of the frame is larger than discord allowed attachment size (with or without nitro), no preview will be sent.",
    #    default=False  # Starts unchecked
    #)# type: ignore
    #discord_custom_tmp_save: bpy.props.StringProperty(
    #    name="Custom rendered tmp save path",
    #    description="Path to custom tmp save for discord's embed message preview frame. default is in the addon prefrences.",
    #    subtype='FILE_PATH',
    #    default=""
    #)  # type: ignore



    
    
    #webhook notifications
    webhook_start: bpy.props.BoolProperty(
        name="Webhook notify on start",
        description="Recive webhook notifications when the render job starts.",
        default=False  # Starts unchecked
    ) # type: ignore
    
    webhook_first: bpy.props.BoolProperty(
        name="Webhook notify on first",
        description="Recive webhook notifications when the first frame has rendered.",
        default=False  # Starts unchecked
    )# type: ignore
    webhook_completion: bpy.props.BoolProperty(
        name="Webhook notify on completion",
        description="Recive webhook notifications when the render job is complete.",
        default=False  # Starts unchecked
    )# type: ignore
    webhook_cancel: bpy.props.BoolProperty(
        name="Webhook notify on cancel",
        description="Recive webhook notifications when the render job is canceled.",
        default=False  # Starts unchecked
    )# type: ignore
    
    
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


class PANEL_LayoutDemo(bpy.types.Panel):
    """Creates a Panel in the render properties tab"""
    bl_label = "Notifications"
    bl_idname = "RENDER_PT_LayoutDemo"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    bl_parent_id = "RENDER_PT_context"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.render_panel_props  # Access our custom property
        
        # Create a collapsible section with a checkbox in the same row
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
        
        # If checkbox is enabled, show additional settings
        if props.is_desktop:
            desktop_col = desktop_box.column()
            desktop_col.label(text="Additional Settings:")
            desktop_col.prop(props, "desktop_start", text="notify on start")
            desktop_col.prop(props, "desktop_first", text="notify on first")
            desktop_col.prop(props, "desktop_completion", text="notify on completion")
            desktop_col.prop(props, "desktop_cancel", text="notify on cancel")
            
        if props.is_discord:
            discord_col = discord_box.column()
            discord_col.label(text="Additional Settings:")
            discord_col.prop(props, "discord_start", text="notify on start")
            discord_col.prop(props, "discord_first", text="notify on first")
            discord_col.prop(props, "discord_completion", text="notify on cancel")
            discord_col.prop(props, "discord_cancel", text="notify on cancel")
            discord_col.prop(props, "discord_preview", text="Enable discord notify")
        
        if props.is_webhook:
            webhook_col = webhook_box.column()
            webhook_col.label(text="Additional Settings:")
            webhook_col.prop(props, "webhook_start", text="notify on start")
            webhook_col.prop(props, "webhook_first", text="notify on first")
            webhook_col.prop(props, "webhook_completion", text="notify on cancel")
            webhook_col.prop(props, "webhook_cancel", text="notify on cancel")

        # Debugging: Print status when checkbox is clicked
        if props.is_desktop:
            layout.label(text="Checkbox is TICKED!", icon="CHECKMARK")
        else:
            layout.label(text="Checkbox is NOT ticked.", icon="CANCEL")
            
        
#if bpy.context.scene.render_panel_props.is_discord:
#    print(f"Checkbox is enabled!: {bpy.context.scene.render_panel_props.discord_preview}")    


# Register & Unregister
classes = [RenderPanelProperties, PANEL_LayoutDemo]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.render_panel_props = bpy.props.PointerProperty(type=RenderPanelProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.render_panel_props
    

if __name__ == "__main__":
    register()
