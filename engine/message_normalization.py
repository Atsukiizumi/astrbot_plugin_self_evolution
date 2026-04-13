from __future__ import annotations


async def normalize_event_message_text(event, dao) -> tuple[str, bool, int]:
    """Normalize an incoming event into stable plain text for downstream cognition logic.

    Returns:
        tuple[str, bool, int]: (text, has_image, image_sub_type)
            - has_image: 是否包含图片
            - image_sub_type: 图片子类型 (0=普通图片, 1=表情包)
    """
    message_obj = getattr(event, "message_obj", None)
    message_chain = getattr(message_obj, "message", None)

    has_image = False
    image_sub_type = 0  # 默认普通图片

    if message_chain:
        try:
            from astrbot.core.message.components import Image

            raw_msg = getattr(message_obj, "raw_message", None)
            image_sub_types = {}
            if raw_msg and hasattr(raw_msg, "get"):
                raw_msg_list = raw_msg.get("message")
                if raw_msg_list:
                    for seg in raw_msg_list:
                        if isinstance(seg, dict) and seg.get("type") == "image":
                            seg_data = seg.get("data", {})
                            if isinstance(seg_data, dict):
                                img_file = seg_data.get("file", "")
                                img_sub_type = seg_data.get("sub_type", 0)
                                if img_file:
                                    image_sub_types[img_file] = img_sub_type

            for comp in message_chain:
                if isinstance(comp, Image):
                    has_image = True
                    comp_file = getattr(comp, "file", "") or ""
                    image_sub_type = image_sub_types.get(comp_file, 0)
                    break
        except (ImportError, ModuleNotFoundError):
            for comp in message_chain:
                if hasattr(comp, "url"):
                    has_image = True
                    break

    if not has_image:
        return event.message_str or "", False, 0

    # sub_type=1 是表情包，返回对应文本
    if image_sub_type == 1:
        return "[表情包]", True, 1
    return "[图片]", True, 0


async def ensure_event_message_text(event, dao) -> tuple[str, bool, int]:
    """Return normalized event text and cache it back onto the event when possible.

    Returns:
        tuple[str, bool, int]: (text, has_image, image_sub_type)
    """
    cached = None
    if hasattr(event, "get_extra"):
        cached = event.get_extra("self_evolution_message_text", None)

    if cached is not None:
        # 返回缓存的值和图片类型
        has_image = getattr(event, "_image_processed", False)
        image_sub_type = getattr(event, "_image_sub_type", 0)
        return cached or event.message_str or "", has_image, image_sub_type

    msg_text, has_image, image_sub_type = await normalize_event_message_text(event, dao)

    if hasattr(event, "set_extra"):
        event.set_extra("self_evolution_message_text", msg_text or "")
    setattr(event, "_image_processed", has_image)
    setattr(event, "_image_sub_type", image_sub_type)

    return msg_text or "", has_image, image_sub_type
