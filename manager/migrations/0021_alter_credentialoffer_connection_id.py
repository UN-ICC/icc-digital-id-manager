# Generated by Django 3.2.19 on 2023-06-29 13:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0020_alter_connectioninvitation_connection_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='credentialoffer',
            name='connection_id',
            field=models.CharField(max_length=100),
        ),
    ]
