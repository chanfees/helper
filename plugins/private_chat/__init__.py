"""私聊对话：好友单聊中直接回复，不加人格或风格限制。"""
from wxbot_framework.llm import LLMError
from wxbot_framework.summary import split_text
from wxbot_framework.text import SYSTEM_PEERS

SYSTEM = """直接回应对方最新一条消息。只输出 JSON 对象：{"reply":"给对方的回复"}。"""

# 文件传输助手不在 SYSTEM_PEERS 中，需要单独排除。
SKIP_PEERS = SYSTEM_PEERS | {"filehelper"}


class Plugin:
    def on_load(self, ctx):
        ctx.llm  # 启动时核对模型配置，不请求接口。

    def on_message(self, message, ctx):
        if (message.type != 1 or message.is_group or message.is_self or
                message.chat_id in SKIP_PEERS or message.data.get("bot_generated") or
                not message.text.strip()):
            return
        try:
            result = ctx.llm.complete_json(SYSTEM, message.text)
            reply = result.get("reply") if isinstance(result, dict) else None
            if (not isinstance(reply, str) or not reply.strip() or len(reply) > 600 or
                    any(ord(char) < 32 and char not in "\n\r\t" for char in reply)):
                raise LLMError("大模型私聊结果格式不正确或过长，请重试")
            for part in split_text(reply.strip()):
                if not ctx.reply(message, part):
                    raise RuntimeError("私聊发送未成功")
            ctx.logger.info("私聊对话完成：chat=%s", message.chat_id)
        except LLMError as error:
            ctx.logger.warning("私聊对话失败：%s", error)
            try:
                ctx.reply(message, "暂时无法回复，请稍后再发。")
            except Exception:
                pass
