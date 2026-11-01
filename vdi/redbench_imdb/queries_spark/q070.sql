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
    n.name_pcode_nf IN ('A45', 'B1264', 'B6514', 'D2142', 'D2531', 'E6245', 'F216', 'J2342', 'M6236', 'R5352', 'T6535', 'V2365')
  )
  AND (
    ci.note IN ('(uncredited)', '(writer)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'cinematographer', 'composer', 'director', 'writer')
  )
  AND (
    it1.id IN ('34')
  )
