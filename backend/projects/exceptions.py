class ProjectError(Exception):
    pass


class ProjectNotFoundError(ProjectError):
    pass


class ProjectValidationError(ProjectError):
    def __init__(self, field_errors: dict[str, list[dict[str, str]]]) -> None:
        self.field_errors = field_errors
        super().__init__("Project validation failed")
