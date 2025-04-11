---
layout: default
title: Archive
---

{% assign postsByCategory = site.posts | group_by: "category" %}
{% for category in postsByCategory %}
  <h2>{{ category.name }}</h2>

  <ul style="margin-bottom: 50px;">
    {% for post in category.items %}
      <li style="margin-bottom: 20px;">
        <a href="{{ post.url }}">{{ post.title }}</a> - {{ post.date | date: "%Y-%m-%d" }}
      </li>
    {% endfor %}
  </ul>
{% endfor %}