SELECT
  n.name,
  mi1.info,
  MIN(t.production_year),
  MAX(t.production_year)
FROM title AS t, kind_type AS kt, movie_info AS mi1, info_type AS it1, cast_info AS ci, role_type AS rt, name AS n
WHERE
  t.id = ci.movie_id
  AND t.id = mi1.movie_id
  AND mi1.info_type_id = it1.id
  AND t.kind_id = kt.id
  AND ci.person_id = n.id
  AND ci.movie_id = mi1.movie_id
  AND ci.role_id = rt.id
  AND (
    it1.id IN ('4')
  )
  AND (
    mi1.info IN ('Catalan', 'Dutch', 'English', 'French', 'Italian', 'Japanese', 'Polish', 'Portuguese', 'Russian', 'Spanish')
  )
  AND (
    n.name ILIKE '%les%'
  )
  AND (
    kt.kind IN ('tv movie', 'video game', 'video movie')
  )
  AND (
    rt.role IN ('cinematographer', 'editor', 'production designer', 'writer')
  )
GROUP BY
  mi1.info,
  n.name
