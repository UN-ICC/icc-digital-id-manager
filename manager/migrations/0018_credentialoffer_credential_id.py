# Generated by Django 3.2.15 on 2022-09-23 14:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0017_add_credentialoffer_revocation_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='credentialoffer',
            name='credential_id',
            field=models.CharField(max_length=250, null=True),
        ),
    ]
