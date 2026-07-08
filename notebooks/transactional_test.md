---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.19.1
  kernelspec:
    display_name: ds-fms-tc-outlook
    language: python
    name: ds-fms-tc-outlook
---

# Testing Listmonk transactional

```python
%load_ext jupyter_black
%load_ext autoreload
%autoreload 2
```

```python
from src.email import listmonk
```

```python
to_emails = [("Tristan Downing", "tristan.downing@un.org")]
cc_emails = [("Zachary Arno", "zachary.arno@un.org")]
```

```python
listmonk.send_transactional(
    to_emails=to_emails,
    cc_emails=cc_emails,
    subject="Listmonk transactional test",
    data={"content": "Test content, populated from Python"},
)
```

```python

```
