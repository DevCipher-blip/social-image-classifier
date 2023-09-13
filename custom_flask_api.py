from flask_restful import Api


class CustomFlaskApi(Api):
    """
    This overridden Flask-RESTful API class will handle and log Internal Server Errors.
    """
    def handle_error(self, e):
        """
        Overrides the handle_error() method of the Api and adds custom error handling.
        """
        print(e)
        code = getattr(e, "code", 500)  # Gets code or defaults to 500
        if code == 500:
            # log internal server errors as CRITICAL
            default_message = "Something went wrong"
            return self.make_response({"message": default_message}, 500)
        return super(CustomFlaskApi, self).handle_error(e)  # handle others the default way
