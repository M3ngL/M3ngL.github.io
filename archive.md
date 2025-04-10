---
layout: default
title: Archive
---

{% assign postsByCategory = site.posts | group_by: "category" %}
{% for category in postsByCategory %}
  <h2>{{ category.name }}</h2>
  <ul>
    {% for post in category.items %}
      <li>
        <a href="{{ post.url }}">{{ post.title }}</a> - {{ post.date | date: "%Y-%m-%d" }}
      </li>
    {% endfor %}
  </ul>
{% endfor %}