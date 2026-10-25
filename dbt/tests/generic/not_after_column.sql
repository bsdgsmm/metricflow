{#- The tested column must not be later than another column of the same row. Nulls pass. -#}
{% test not_after_column(model, column_name, other_column) %}

select
    {{ column_name }},
    {{ other_column }}
from {{ model }}
where {{ column_name }} > {{ other_column }}

{% endtest %}
