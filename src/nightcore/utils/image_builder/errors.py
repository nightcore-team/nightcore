"""Custom exceptions for image builder."""


class ImageNotLoadedError(Exception):
    """Exception raised when an image operation is attempted on an unloaded image."""  # noqa: E501

    def __init__(self, message: str | None = None):
        self.message = (
            message or "Cannot perform operation: image is not loaded"
        )
        super().__init__(self.message)
