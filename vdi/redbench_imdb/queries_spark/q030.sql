SELECT
  COUNT(*)
FROM title AS t, kind_type AS kt, info_type AS it1, movie_info AS mi1, movie_info AS mi2, info_type AS it2, cast_info AS ci, role_type AS rt, name AS n, movie_keyword AS mk, keyword AS k
WHERE
  t.id = ci.movie_id
  AND t.id = mi1.movie_id
  AND t.id = mi2.movie_id
  AND t.id = mk.movie_id
  AND k.id = mk.keyword_id
  AND mi1.movie_id = mi2.movie_id
  AND mi1.info_type_id = it1.id
  AND mi2.info_type_id = it2.id
  AND (
    it1.id IN ('4')
  )
  AND (
    it2.id IN ('5')
  )
  AND t.kind_id = kt.id
  AND ci.person_id = n.id
  AND ci.role_id = rt.id
  AND (
    mi1.info IN ('English')
  )
  AND (
    mi2.info IN ('Canada:18A', 'New Zealand:R18', 'Singapore:PG13', 'UK:E', 'USA:T')
  )
  AND (
    kt.kind IN ('episode', 'movie', 'video movie')
  )
  AND (
    rt.role IN ('actress', 'writer')
  )
  AND (
    n.gender IN ('f') OR n.gender IS NULL
  )
  AND (
    t.production_year <= 2015
  )
  AND (
    t.production_year >= 1990
  )
  AND (
    k.keyword IN ('anal-sex', 'bare-chested-male', 'blood', 'cigarette-smoking', 'dancing', 'doctor', 'gay', 'lesbian', 'male-nudity', 'oral-sex', 'police', 'song')
  )
