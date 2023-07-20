# Generated by Django 3.1 on 2020-11-10 15:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0006_auto_20201105_1007"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="credentialdefinition",
            name="credential_json",
        ),
        migrations.AddField(
            model_name="credentialdefinition",
            name="support_revocation",
            field=models.BooleanField(default=True),
        ),
    ]
