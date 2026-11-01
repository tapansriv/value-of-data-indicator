SELECT
  COUNT(*)
FROM name AS n, aka_name AS an, info_type AS it1, person_info AS pi1, cast_info AS ci, role_type AS rt
WHERE
  n.id = ci.person_id
  AND ci.person_id = pi1.person_id
  AND it1.id = pi1.info_type_id
  AND n.id = pi1.person_id
  AND n.id = an.person_id
  AND ci.person_id = an.person_id
  AND an.person_id = pi1.person_id
  AND rt.id = ci.role_id
  AND (
    n.gender IN ('m') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('B6321', 'B6524', 'D52', 'E6242', 'G6351', 'J546', 'M2123', 'N532', 'P3625', 'R1634', 'R4531', 'S3635', 'W4512')
  )
  AND (
    ci.note IN ('(executive producer)', '(voice)', '(writer)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'composer', 'director', 'producer', 'writer')
  )
  AND (
    it1.id IN ('37')
  )
