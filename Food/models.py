from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import F, Value, Max, Avg, Count
from django.templatetags.static import static
from model_utils.managers import InheritanceManager
from Config import tools
import datetime

def static_url(url):
    return f"{settings.DOMAIN_ADDRESS}{static(url)}"

def domain_url(url):
    return f"{settings.DOMAIN_ADDRESS}{url}"



class Gallery(models.Model):
    title = models.CharField(max_length=100)

    def __str__(self):
        if self.title:
            return f"Gallery - {self.title[:30]}"
        return f"Gallery"

    def get_images(self):
        return self.image_set.all()

    def get_src_directory(self):
        # title = str(self.title).replace(' ', '-')
        # return f"{title}-{self.id}"
        return tools.RandomString(40)


def upload_image_gallery_src(instance, path):
    path = str(path).split('.')[-1]
    if path in settings.IMAGES_FORMAT:
        src = f"images/gallery/{instance.gallery.get_src_directory()}/{tools.RandomString(40)}.{path}"
        return src
    raise PermissionDenied


class Image(models.Model):
    image = models.ImageField(upload_to=upload_image_gallery_src)
    gallery = models.ForeignKey('Gallery', on_delete=models.CASCADE)

    def __str__(self):
        return f"Image - {self.gallery.title}"


class Category(models.Model):
    title = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    @property
    def title_slug(self):
        return str(self.title).replace(' ', '-')

    @property
    def slug(self):
        return str(self.title).replace(' ', '-')



class CustomManagerMeal(InheritanceManager):
    use_for_related_fields = True

    def get_queryset(self):
        return super().get_queryset().filter(category__is_active=True, status_show='show', stock__gt=0)

    def all(self):
        return self.get_queryset().select_subclasses()

    def get_with_discount(self):
        meals = Meal.get_objects.all()
        meals_discount = []
        for meal in meals:
            if meal.get_max_discount() != None:
                meals_discount.append(meal)
        return meals_discount

    def sort_by_popularity(self):
        meals = Meal.get_objects.all()
        return sorted(meals,key=lambda meal : meal.get_comments_rate_avg())


    def get_by_slug(self,slug):
        ID = str(slug).split('-')[-1]
        if ID:
            try:
                return Meal.get_objects.get(id=ID)
            except:
                pass
        return None


class MealBase(models.Model):
    STATUS_SHOW = (
        ('show', 'Show'),
        ('hide', 'Hide')
    )


    title = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    gallery = models.ForeignKey('Gallery', on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    price = models.DecimalField(decimal_places=2, max_digits=10)
    stock = models.IntegerField(default=0)
    status_show = models.CharField(default='show', choices=STATUS_SHOW, max_length=10)

    # Default Manager
    objects = models.Manager()
    # Custome Manager
    get_objects = CustomManagerMeal()

    class Meta:
        abstract = True

    def __str__(self):
        return self.title[:30]

    @property
    def title_slug(self):
        return str(self.title).replace(' ', '-')

    @property
    def slug(self):
        return f"{str(self.title).replace(' ', '-')}-{self.id}"

    def get_price(self,discount=None):
        if discount == None:
            discount = self.get_max_discount()
        price = self.price
        if discount:
            price_with_discount = price - ((price / 100) * discount.percentage)
            if price_with_discount >= 0:
                price = price_with_discount
        price = tools.get_decimal_num(price,2)
        return price

    def get_max_discount(self):
        return self.discount_set.all().order_by('-percentage').first()

    def get_images(self):
        galley = self.gallery
        if galley:
            return galley.get_images()
        return []

    def get_image_cover(self):
        first_image =  tools.GetValueInList(self.get_images(),0)
        if first_image != None:
            return domain_url(first_image.image.url)
        return static_url('images/image-not-found.png')

    def is_available_stock(self):
        return True if int(self.stock) > 0 else False

    def get_comments(self):
        return Comment.get_objects.get_comments_by_meal(self)

    def get_comments_rate_avg(self):
        return Comment.get_objects.get_average(self)

    def get_comments_count(self):
        return Comment.get_objects.get_count_comments(self)




class Meal(MealBase):
    objects = InheritanceManager()


class Food(Meal):
    type_meal = models.CharField(default='food', editable=False, max_length=10)


class Drink(Meal):
    type_meal = models.CharField(default='drink', editable=False, max_length=10)


class MealGroup(Meal):
    """
        Group includes Food and Drink and . . . Other Meals
    """
    type_meal = models.CharField(default='group', editable=False, max_length=10)
    foods = models.ManyToManyField('Food')
    drinks = models.ManyToManyField('Drink')



class Discount(models.Model):
    title = models.CharField(max_length=100,null=True,blank=True)
    percentage = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    meals = models.ManyToManyField('Meal')
    # !Note Date cannot be in the past
    time_end = models.DateTimeField()

    def __str__(self):
        return self.title[:40]





class CustomeManagerComment(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_checked=True)

    def get_comments_by_meal(self,meal):
        return self.get_queryset().filter(meal=meal)

    def get_comments_by_user(self,user):
        return self.filter(user=user)

    def get_average(self,meal):
        avg = self.get_comments_by_meal(meal).aggregate(avg=Avg('rate'))['avg'] or 0
        return tools.get_decimal_num(avg)

    def get_count_comments(self,meal):
        return self.get_comments_by_meal().count()


class Comment(models.Model):
    user = models.ForeignKey('User.User',on_delete=models.CASCADE)
    meal = models.ForeignKey('Meal',on_delete=models.CASCADE)
    rate = models.IntegerField(validators=[MinValueValidator(1),MaxValueValidator(5)])
    title = models.CharField(max_length=100)
    text = models.TextField()
    send_time = models.DateTimeField(auto_now_add=True)
    is_checked = models.BooleanField(default=False)

    # Default Manager
    objects = models.Manager()
    # Custome Manager
    get_objects = CustomeManagerComment()


    def __str__(self):
        return tools.TextToShortText(self.title,30)


    def get_rate_state(self):
        if self.rate > 3:
            return '+'
        elif self.rate == 3:
            return '='
        else:
            return '-'