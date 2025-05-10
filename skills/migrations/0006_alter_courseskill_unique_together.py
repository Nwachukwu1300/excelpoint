# Generated manually

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('skills', '0005_userskill'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='courseskill',
            unique_together={('course', 'skill')},
        ),
    ] 