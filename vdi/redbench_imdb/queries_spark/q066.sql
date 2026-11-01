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
    n.gender IN ('m')
  )
  AND (
    n.name_pcode_nf IN ('A5353', 'B6534', 'C625', 'D1315', 'D5452', 'E6216', 'E6253', 'J5416', 'M2454', 'M6241', 'P3625', 'P3632', 'S3125', 'W4562')
  )
  AND (
    ci.note IS NULL
  )
  AND (
    rt.role IN ('actor')
  )
  AND (
    it1.id IN ('19')
  )
