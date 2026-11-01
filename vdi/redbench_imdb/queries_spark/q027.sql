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
    it1.id IN ('1')
  )
  AND (
    it2.id IN ('18')
  )
  AND t.kind_id = kt.id
  AND ci.person_id = n.id
  AND ci.role_id = rt.id
  AND (
    mi1.info IN ('30', '60')
  )
  AND (
    mi2.info IN ('CBS Studio Center - 4024 Radford Avenue, Studio City, Los Angeles, California, USA', 'Los Angeles, California, USA', 'Paramount Studios - 5555 Melrose Avenue, Hollywood, Los Angeles, California, USA', 'Stage 22, Warner Brothers Burbank Studios - 4000 Warner Boulevard, Burbank, California, USA', 'Warner Brothers Burbank Studios - 4000 Warner Boulevard, Burbank, California, USA')
  )
  AND (
    kt.kind IN ('tv series', 'video game')
  )
  AND (
    rt.role IN ('editor')
  )
  AND (
    n.gender IN ('m')
  )
  AND (
    t.production_year <= 2015
  )
  AND (
    t.production_year >= 1925
  )
