import pgvector.django.indexes
import pgvector.django.vector
from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):

    dependencies = [
        ('subjects', '0015_drop_targeted_practice'),
    ]

    operations = [
        VectorExtension(),
        # JSON '[0.1, ...]' text is valid pgvector input; there is no direct jsonb -> vector cast
        migrations.RunSQL(
            sql='ALTER TABLE subjects_contentchunk ALTER COLUMN embedding_vector '
                'TYPE vector(384) USING embedding_vector::text::vector(384)',
            reverse_sql='ALTER TABLE subjects_contentchunk ALTER COLUMN embedding_vector '
                        'TYPE jsonb USING embedding_vector::text::jsonb',
            state_operations=[
                migrations.AlterField(
                    model_name='contentchunk',
                    name='embedding_vector',
                    field=pgvector.django.vector.VectorField(blank=True, dimensions=384, null=True),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name='contentchunk',
            index=pgvector.django.indexes.HnswIndex(fields=['embedding_vector'], name='chunk_embedding_hnsw', opclasses=['vector_cosine_ops']),
        ),
    ]
