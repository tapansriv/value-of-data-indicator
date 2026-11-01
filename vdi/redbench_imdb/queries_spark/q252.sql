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
    n.gender IN ('f', 'm') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('A2354', 'A5252', 'B2632', 'C6516', 'D1341', 'E3625', 'H434', 'J2513', 'J526', 'K525', 'L253', 'L456', 'M241', 'M3242', 'M6524', 'R2525', 'R416', 'S252', 'S3526', 'T5635', 'W4541', 'W4542')
  )
  AND (
    ci.note IN ('(animation producer)', '(book)', '(co-executive producer)', '(executive producer)', '(linear editor)', '(producer)', '(production accountant)', '(production assistant)', '(production runner)', '(supervising producer)', '(uncredited)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'cinematographer', 'editor', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('37')
  )
