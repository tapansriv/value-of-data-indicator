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
    it1.id IN ('16')
  )
  AND (
    it2.id IN ('2')
  )
  AND t.kind_id = kt.id
  AND ci.person_id = n.id
  AND ci.role_id = rt.id
  AND (
    mi1.info IN ('USA:2003', 'USA:2004', 'USA:2006', 'USA:2008', 'USA:2009', 'USA:2010', 'USA:2012')
  )
  AND (
    mi2.info IN ('Color')
  )
  AND (
    kt.kind IN ('episode', 'movie', 'video movie')
  )
  AND (
    rt.role IN ('cinematographer')
  )
  AND (
    n.gender IN ('f')
  )
  AND (
    t.production_year <= 2015
  )
  AND (
    t.production_year >= 1990
  )
  AND (
    k.keyword IN ('anal-sex', 'bare-chested-male', 'based-on-novel', 'blood', 'cigarette-smoking', 'dancing', 'death', 'fight', 'flashback', 'friendship', 'independent-film', 'jealousy', 'love', 'non-fiction', 'number-in-title', 'party', 'police', 'sequel', 'sex', 'surrealism')
  )
