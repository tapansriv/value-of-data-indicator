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
    n.name_pcode_nf IN ('B4521', 'B6535', 'C24', 'C6425', 'I2163', 'I5263', 'J252', 'K3615', 'L2363', 'R3264', 'S4152', 'T2563', 'T5252')
  )
  AND (
    ci.note IN ('(dialogue) (uncredited)', '(producer)', '(uncredited)', '(voice)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'composer', 'producer', 'writer')
  )
  AND (
    it1.id IN ('22')
  )
