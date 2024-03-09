.. _summarization-label:

Summarization
=============

Models
------

+-----------------------------------------------------------------------+-------+
| Model                                                                 | Lang  |
+=======================================================================+=======+
| `mrm8488/bert-mini2bert-mini-finetuned-cnn_daily_mail-summarization   | EN    |
| <https://huggingface.co/mrm8488/bert-mini2bert-mini-                  |       |
| finetuned-cnn_daily_mail-summarization>`__                            |       |
+-----------------------------------------------------------------------+-------+
| `nandakishormpai/t5-small-machine-articles-tag-generation             | EN    |
| <https://huggingface.co/nandakishormpai                               |       |
| /t5-small-machine-articles-tag-generation>`__                         |       |
+-----------------------------------------------------------------------+-------+
| `mrm8488/bert-small2bert-small-finetuned-cnn_daily_mail-summarization | EN    |
| <https://huggingface.co/mrm8488/bert-small2bert-                      |       |
| small-finetuned-cnn_daily_mail-summarization>`__                      |       |
+-----------------------------------------------------------------------+-------+
| `stevhliu/my_awesome_billsum_model                                    | RU    |
| <https://huggingface.co/stevhliu/my_awesome_billsum_model>`__         |       |
+-----------------------------------------------------------------------+-------+
| `UrukHan/t5-russian-summarization                                     | RU    |
| <https://huggingface.co/UrukHan/t5-russian-summarization>`__          |       |
+-----------------------------------------------------------------------+-------+
| `dmitry-vorobiev/rubert_ria_headlines                                 | RU    |
| <https://huggingface.co/dmitry-vorobiev/rubert_ria_headlines>`__      |       |
+-----------------------------------------------------------------------+-------+


Datasets
--------

1. `ccdv/govreport-summarization <https://huggingface.co/datasets/ccdv/govreport-summarization>`__

   1. **Lang**: EN
   2. **Rows**: 973
   3. **Preprocess**:

      1. Rename column ``report`` to ``source``.
      2. Rename column ``summary`` to ``target``.
      3. Reset indexes.

2. `cnn_dailymail <https://huggingface.co/datasets/cnn_dailymail>`__

   1. **Lang**: EN
   2. **Rows**: 11490
   3. **Preprocess**:

      1. Select ``1.0.0`` subset.
      2. Drop columns ``id``.
      3. Rename column ``article`` to ``source``.
      4. Rename column ``highlights`` to ``target``.
      5. Delete duplicates in dataset.
      6. Remove substring ``(CNN)`` for each ``source`` row.
      7. Reset indexes.

3. `tomasg25/scientific_lay_summarisation <https://huggingface.co/datasets/tomasg25/scientific_lay_summarisation>`__

   1. **Lang**: EN
   2. **Rows**: 1376
   3. **Preprocess**:

      1. Select ``plos`` subset.
      2. Drop columns ``section_headings``, ``keywords``, ``title``, ``year``.
      3. Rename column ``article`` to ``source``.
      4. Rename column ``summary`` to ``target``.
      5. Reset indexes.

4. `ccdv/pubmed-summarization <https://huggingface.co/datasets/ccdv/pubmed-summarization?row=0>`__

   1. **Lang**: EN
   2. **Rows**: 6658
   3. **Preprocess**:

      1. Rename column ``article`` to ``source``.
      2. Rename column ``abstract`` to ``target``.
      3. Reset indexes.

5. `IlyaGusev/gazeta <https://huggingface.co/datasets/IlyaGusev/gazeta>`__

   1. **Lang**: RU
   2. **Rows**: 6793
   3. **Preprocess**:

      1. Drop columns ``title``, ``date``, ``url``.
      2. Rename column ``text`` to ``source``.
      3. Rename column ``summary`` to ``target``.
      4. Reset indexes.

6. `d0rj/curation-corpus-ru <https://huggingface.co/datasets/d0rj/curation-corpus-ru>`__

   1. **Lang**: RU
   2. **Rows**: 30454
   3. **Preprocess**:

      1. Select ``train`` split.
      2. Drop columns ``title``, ``date``, ``url``.
      3. Rename column ``article_content`` to ``source``.
      4. Rename column ``summary`` to ``target``.
      5. Reset indexes.

7. `CarlBrendt/Summ_Dialog_News <https://huggingface.co/datasets/CarlBrendt/Summ_Dialog_News?row=1>`__

   1. **Lang**: RU
   2. **Rows**: 7609
   3. **Preprocess**:

      1. Rename column ``info`` to ``source``.
      2. Rename column ``summary`` to ``target``.
      3. Reset indexes.

8. `trixdade/reviews_russian <https://huggingface.co/datasets/trixdade/reviews_russian>`__

   1. **Lang**: RU
   2. **Rows**: 95
   3. **Preprocess**:

      1. Select ``train`` split.
      2. Rename column ``Reviews`` to ``source``.
      3. Rename column ``Summary`` to ``target``.
      4. Reset indexes.


Metrics
-------

-  BLEU
-  ROUGE

.. note:: Use the ``rougeL`` metric and set ``seed=77`` parameter
          when loading the rouge metric.
