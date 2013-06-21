
# extend the usual date parsing with:
# - optional matching by adding a trailing ?
# - (nestable) grouping and alternatives as (A|B|C)
# - matching of variable space %* and %+
# - modify matchers for textual day, month, timezone that match any string
#   by adding a trailing !
# - an additional timezone %: (like %z but with a colon between H and M)
# - generation of the "equivalent format" for display after parsing

# so the following are similar:
# ISO_8601 = add_timezone('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%Y')
# %Y(-%m(-%d((%+|T)%H:%M(:%S(.%f)?)?))?)?%*(%Z!|%z|%:)?