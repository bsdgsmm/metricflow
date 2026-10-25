{#- Whole calendar months from the month of `earlier` to the month of `later`. -#}
{% macro months_between(later, earlier) -%}
    (
        (extract(year from {{ later }}) - extract(year from {{ earlier }})) * 12
        + extract(month from {{ later }}) - extract(month from {{ earlier }})
    )::integer
{%- endmacro %}
