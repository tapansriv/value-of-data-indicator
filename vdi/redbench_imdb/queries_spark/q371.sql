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
    it1.id IN ('8')
  )
  AND (
    it2.id IN ('6')
  )
  AND t.kind_id = kt.id
  AND ci.person_id = n.id
  AND ci.role_id = rt.id
  AND (
    mi1.info IN ('Argentina', 'Bulgaria', 'Canada', 'Germany', 'India', 'Italy', 'Mexico', 'Netherlands', 'Sweden', 'UK')
  )
  AND (
    mi2.info IN ('Dolby Digital', 'Dolby SR', 'Dolby', 'Mono', 'Stereo')
  )
  AND (
    kt.kind IN ('tv movie', 'tv series', 'video game')
  )
  AND (
    rt.role IN ('miscellaneous crew')
  )
  AND (
    n.gender IN ('f')
  )
  AND (
    t.production_year <= 2015
  )
  AND (
    t.production_year >= 1975
  )
  AND (
    k.keyword IN ('4th-century-b.c.', 'blindness-caused-by-boxing', 'bombing-victim', 'circus-giant', 'decamerotic', 'eaten-by-shark', 'exploding-dam', 'glass-vase', 'indigenous-language', 'ithaca-college', 'la-vida-loca', 'lancet', 'meekness', 'modern-medicine', 'no-soundtrack', 'pet-trick', 'pink-lips', 'pizza-delivery', 'reference-to-avalokiteshvara', 'reference-to-the-hope-diamond', 'skinny-dipping', 'spelling', 'stick-fight')
  )
