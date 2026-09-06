from notifications.interfaces import EmailSenderInterface


class StubEmailSender(EmailSenderInterface):
    async def send_activation_email(self, email: str, activation_link: str) -> None:
        pass

    async def send_activation_complete_email(self, email: str, login_link: str) -> None:
        pass

    async def send_password_reset_email(self, email: str, reset_link: str) -> None:
        pass

    async def send_password_reset_complete_email(self, email: str, login_link: str) -> None:
        pass

    async def send_reply_to_comment_email(
            self,
            email: str,
            movie_name: str,
            replier_email: str,
            reply_text: str
    ) -> None:
        pass