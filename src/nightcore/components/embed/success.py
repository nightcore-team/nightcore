from discord import Color, Embed


class SuccessMoveEmbed(Embed):
    def __init__(
        self,
        title: str,
        description: str,
        footer_text: str,
        footer_icon_url: str,
    ):
        super().__init__(
            title=title,
            description=description,
            color=Color.green(),
        )
        self.set_footer(text=footer_text, icon_url=footer_icon_url)
