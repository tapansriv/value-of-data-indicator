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
    it1.id IN ('6')
  )
  AND (
    it2.id IN ('5')
  )
  AND t.kind_id = kt.id
  AND ci.person_id = n.id
  AND ci.role_id = rt.id
  AND (
    mi1.info IN ('Dolby Digital', 'Mono', 'Stereo')
  )
  AND (
    mi2.info IN ('Australia:PG', 'Canada:G', 'Iceland:16', 'Netherlands:12', 'Portugal:M/16', 'South Korea:15', 'USA:Not Rated')
  )
  AND (
    kt.kind IN ('tv movie', 'tv series', 'video game')
  )
  AND (
    rt.role IN ('producer')
  )
  AND (
    n.gender IN ('m')
  )
  AND (
    t.production_year <= 2015
  )
  AND (
    t.production_year >= 1975
  )
  AND (
    k.keyword IN ('arena-theatre', 'bathing-girl', 'czechoslovakian-soldier', 'daisy-dukes', 'dead-camel', 'dog-rescue', 'escort-plane', 'favela', 'horse-wrangler', 'humsafar', 'italian-pastry', 'police-officer-drowned', 'post-traumatic-fairytale', 'practical-special-effects', 'quebec-separatism', 'reference-to-havelock-ellis', 'reference-to-richard-simmons', 'reference-to-sears-roebuck', 'reference-to-sinead-oconnor', 'romantic-situation', 'sailboating', 'schoolhouse', 'storm-chaser', 'tuft-of-hair', 'two-in-a-phone-booth')
  )
