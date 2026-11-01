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
    n.gender IN ('f', 'm')
  )
  AND (
    n.name_pcode_nf IN ('A4536', 'B4241', 'B5165', 'C5254', 'C6252', 'D1316', 'D1325', 'G1641', 'H6243', 'K3625', 'L616', 'M5142', 'N2132', 'S4524', 'T521', 'V6254', 'W4132', 'Y2526')
  )
  AND (
    ci.note IN ('(co-executive producer)', '(executive producer)', '(voice)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'producer')
  )
  AND (
    it1.id IN ('37')
  )
