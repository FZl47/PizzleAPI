# Generated by Django 3.2 on 2022-07-28 10:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('User', '0004_auto_20220728_1500'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='address',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='User.address'),
        ),
        migrations.AddField(
            model_name='order',
            name='detail',
            field=models.TextField(blank=True, null=True),
        ),
    ]