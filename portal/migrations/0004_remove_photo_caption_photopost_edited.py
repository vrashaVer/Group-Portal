# Generated by Django 5.1.2 on 2024-11-09 09:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0003_photopost_photo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='photo',
            name='caption',
        ),
        migrations.AddField(
            model_name='photopost',
            name='edited',
            field=models.BooleanField(default=False),
        ),
    ]
