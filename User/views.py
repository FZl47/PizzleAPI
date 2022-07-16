from django.shortcuts import render
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import get_template
from django.template import Context
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from Config.permissions import IsAuthenticated
from Config import task
from Config import redis_py
from Config import tools
from Config.response import Response
from Config import exceptions
from .serializers import UserBasicSerializer

_loop = task.Loop()


def get_user_by_email(email):
    User = get_user_model()
    try:
        return User.objects.get(email=email)
    except:
        return None


def get_user_by_email_password(email, password):
    try:
        User = get_user_model()
        user = User.objects.get(email=email)
        if user.check_password(password):
            return user
        return None
    except:
        return None


def create_tokens_jwt(user):
    refresh_token = RefreshToken.for_user(user)
    return {
        'refresh_token': str(refresh_token),
        'access_token': str(refresh_token.access_token)
    }


class GetAccessToken(APIView):
    """
          Get fields = [refresh]
          Auth = False
    """

    def post(self, request):
        # Response info
        status_code = None
        error_response = ''
        message_response = ''
        data_response = {}

        data = request.data
        refresh = data.get('refresh')
        if refresh:
            try:
                access = RefreshToken(refresh).access_token
                if access:
                    status_code = 200
                    data_response['access'] = str(access)
            except:
                raise exceptions.TokenExpiredOrInvalid()
        else:
            raise exceptions.TokenExpiredOrInvalid()
        return Response(status_code, data_response, message=message_response, error=error_response)


class LoginUser(APIView):
    """
        Get fields = [email, password]
        Auth = False
    """

    def post(self, request):
        # Response info
        status_code = None
        error_response = ''
        message_response = ''
        data_response = {}

        data = request.data
        email = data.get('email')
        password = data.get('password')
        if email and password:
            user = get_user_by_email_password(email, password)
            if user:
                data_response = create_tokens_jwt(user)
                status_code = 200
                message_response = 'WelCome'
            else:
                raise exceptions.UserNotFound()
        else:
            raise exceptions.FieldsIsEmpty()

        return Response(status_code, data_response, message=message_response, error=error_response)


class RegisterUser(APIView):
    """
            Get fields = [email, password, password2]
            Auth = False
    """

    def post(self, request):
        # Response info
        status_code = None
        error_response = ''
        message_response = ''
        data_response = {}

        data = request.data
        email = data.get('email')
        password = data.get('password')
        password2 = data.get('password2')
        if email and password and password2:
            if password == password2:
                user = get_user_by_email(email)
                if not user:
                    user = get_user_model().objects.create(email=email)
                    user.set_password(password)
                    data_response = create_tokens_jwt(user)
                    status_code = 200
                    message_response = 'Your account created successfuly'
                else:
                    raise exceptions.UserAlreadyExsists()
            else:
                raise exceptions.PasswordsNotMatch()
        else:
            raise exceptions.FieldsIsEmpty()

        return Response(status_code, data_response, message=message_response, error=error_response)


class ResetPasswordGetCode(APIView):
    """
        Get fields = [email]
        Auth = False
    """

    def resetCode(self, email):
        code = tools.RandomString(5)
        email = f"Email_Reset_{email}"
        # After 5 minutes code will delete
        redis_py.set_value_expire(email, code, 299)
        return code

    def _send_email_target(self, email):
        code = self.resetCode(email)
        subject = 'Food Shop - Reset Password'
        template_html = get_template('email_template.html')
        context = {'code': code}
        content_html = template_html.render(context)
        _email = EmailMultiAlternatives(subject, '', settings.EMAIL_HOST_USER, [email])
        _email.attach_alternative(content_html, "text/html")
        _email.send()

    def post(self, request):
        # Response info
        status_code = None
        error_response = ''
        message_response = ''
        data_response = {}

        data = request.data
        email = data.get('email')
        if email:
            user = get_user_by_email(email)
            if user:
                # Checking the code has been sended or not
                code_is_sended = False if redis_py.get_value(f"Email_Reset_{email}") == None else True
                if not code_is_sended:
                    # Add task to loop for run in background
                    t = task.Task(self._send_email_target, args=(email,))
                    _loop.add(t)
                    _loop.start_thread()
                    status_code = 200
                    message_response = 'The recovery code has been sent to your email'
                    data_response = {
                        'email': email
                    }
                else:
                    status_code = 226
                    message_response = 'The recovery code has been sended to your email'
                    data_response = {
                        'email': email
                    }
            else:
                raise exceptions.UserNotFoundWithEmail()
        else:
            raise exceptions.EmailFieldIsEmpty()
        return Response(status_code, data_response, message=message_response, error=error_response)


class ResetPasswordValidateCode(APIView):
    """
            Get fields = [email, code]
            Auth = False
    """

    def post(self, request):
        # Response info
        status_code = None
        error_response = ''
        message_response = ''

        data = request.data
        email = data.get('email')
        code_get = data.get('code')
        if email and code_get:
            user = get_user_by_email(email)
            if user:
                code_sened = redis_py.get_value(f"Email_Reset_{email}")

                if (code_sened) and (code_sened == code_get):
                    # Set 5 minutes for access to submit new password
                    redis_py.set_value_expire(f"Email_Reset_{email}_Code_{code_get}", 'True', 299)
                    redis_py.remove_key(f"Email_Reset_{email}")
                    status_code = 200
                    data_response = {
                        'email': email,
                        'code': code_get
                    }
                else:
                    raise exceptions.InvalidCode()
            else:
                raise exceptions.UserNotFoundWithEmail()
        else:
            raise exceptions.InvalidEmailOrCode()
        return Response(status_code, data_response, message=message_response, error=error_response)


class ResetPasswordSetPassword(APIView):
    """
        Get fields = [email, code, password, password2]
        Auth = False
    """

    def post(self, request):
        # Response info
        status_code = None
        error_response = ''
        message_response = ''
        data_response = {}

        data = request.data
        email = data.get('email')
        code_get = data.get('code')
        password_1 = data.get('password')
        password_2 = data.get('password2')

        if email and code_get and password_1 and password_1:
            user = get_user_by_email(email)
            if user:
                access_to_set_password = True if redis_py.get_value(
                    f"Email_Reset_{email}_Code_{code_get}") != None else False
                if access_to_set_password:
                    if password_1 == password_2:
                        user.set_password(password_1)
                        user.save()
                        status_code = 200
                        message_response = 'Your new password has been created successfully'
                        redis_py.remove_key(f"Email_Reset_{email}_Code_{code_get}")
                    else:
                        raise exceptions.PasswordsNotMatch()
                else:
                    raise exceptions.ForbiddenAction()
            else:
                raise exceptions.UserNotFoundWithEmail()
        else:
            raise exceptions.FieldsIsEmpty()
        return Response(status_code, data_response, message=message_response, error=error_response)


class AddToCart(APIView):
    """
        Get fields = [
        slug,
        count=optional : Default 1
        ]
        Auth = True
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        # Response info
        status_code = None
        error_response = ''
        message_response = ''
        data_response = {}

        data = request.data
        slug = data.get('slug') or ''
        count = data.get('count') or 1
        added_to_cart = request.user.add_to_cart(slug,count)
        if added_to_cart:
            status_code = 200
            message_response = 'Added to cart successfuly'
        else:
            raise exceptions.ProblemAddToCart()
        return Response(status_code, data_response, message_response, error_response)


class GetUser(APIView):
    """
            Get fields = []
            Auth = True
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        data_response = {}
        user = request.user
        if user.is_authenticated:
            data_response = {
                'user': UserBasicSerializer(user).data
            }
            return Response(200, data_response)
        raise exceptions.UserNotFound()
