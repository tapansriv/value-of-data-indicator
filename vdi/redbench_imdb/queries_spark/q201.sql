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
    mi1.info IN ('Dutch', 'English', 'German')
  )
  AND (
    mi2.info IN ('Australia:PG', 'Belgium:KT', 'Canada:PG', 'Finland:K-16', 'Finland:S', 'Sweden:Btl', 'UK:PG', 'USA:Approved', 'USA:Passed', 'USA:R', 'West Germany:12', 'West Germany:16')
  )
  AND (
    kt.kind IN ('movie', 'tv movie')
  )
  AND (
    rt.role IN ('actress')
  )
  AND (
    n.gender IN ('m')
  )
  AND (
    t.production_year <= 1975
  )
  AND (
    t.production_year >= 1875
  )
  AND (
    k.keyword IN ('anal-sex', 'based-on-novel', 'death', 'gun', 'hardcore', 'homosexual', 'hospital', 'husband-wife-relationship', 'lesbian-sex', 'marriage', 'number-in-title', 'oral-sex', 'singing', 'suicide')
  )
