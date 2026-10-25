{#- Values must fall inside an inclusive range; either bound may be omitted. Nulls pass. -#}
{% test between(model, column_name, min_value=none, max_value=none) %}

    select {{ column_name }}
    from {{ model }}
    where
        {{ column_name }} < {{ min_value if min_value is not none else 'null' }}
        or {{ column_name }} > {{ max_value if max_value is not none else 'null' }}

{% endtest %}
