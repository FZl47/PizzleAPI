from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import ugettext_lazy as _
from django.db import models
from Food.models import Meal, NotifyMe
from Config import tools



class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=70, null=True, default='Unknown')
    last_name = models.CharField(max_length=70, null=True, default='Unknown')
    phone_number = models.CharField(max_length=15, null=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def getName(self):
        return f'{self.first_name} {self.last_name}'

    def __str__(self):
        return self.getName()

    def add_to_cart(self,slug,count=1):
        count = str(count)
        if count.isdigit():
            count = int(count)
        else:
            count = 1
        meal = Meal.get_objects.get_by_slug(slug)
        if meal:
            if meal.stock > 0:
                order = self.get_order_active()
                orderDetails = order.get_details()
                orderDetail = orderDetails.filter(meal=meal).first()
                if orderDetail:
                    old_count = orderDetail.count
                    new_count = old_count + count
                    if new_count <= meal.stock:
                        orderDetail.count = new_count
                    else:
                        orderDetail.count = meal.stock
                    orderDetail.save()
                else:
                    OrderDetail.objects.create(order=order,meal=meal,count=count)
                return True
        return False

    def get_order_active(self):
        order = self.order_set.filter(is_paid=False).first()
        if order == None:
            order = Order.objects.create(user=self)
        return order

    def in_my_notify(self,meal):
        notify = self.get_notify(meal)
        return True if notify != None else False

    def get_notify(self,meal):
        return self.notifyme_set.filter(meal=meal).first()


class Order(models.Model):
    user = models.ForeignKey('User',on_delete=models.CASCADE)
    details_meals = models.TextField(null=True,blank=True)
    is_paid = models.BooleanField(default=False)
    time_pay = models.DateTimeField(null=True,blank=True)
    price_paid = models.PositiveIntegerField(null=True,blank=True)

    def get_details(self):
        return self.orderdetail_set.all()





    def __str__(self):
        return f"Order - {self.user.getName()}"


class OrderDetail(models.Model):
    order = models.ForeignKey('Order',on_delete=models.CASCADE)
    meal = models.ForeignKey('Food.Meal',on_delete=models.SET_NULL,null=True,blank=True)
    count = models.IntegerField(default=1)
    detail = models.TextField(null=True)

    def __str__(self):
        return f'OrderDetail - {tools.TextToShortText(self.meal.title,30)}'



