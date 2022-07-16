# Generated by Django 3.2 on 2022-07-15 23:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Food', '0012_notifyme'),
        ('User', '0002_order'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='meals',
        ),
        migrations.CreateModel(
            name='OrderDetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count', models.IntegerField(default=1)),
                ('detail', models.TextField(null=True)),
                ('meal', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='Food.meal')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='User.order')),
            ],
        ),
    ]