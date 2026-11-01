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
    n.name_pcode_nf IN ('A5364', 'B1542', 'B6352', 'C6425', 'C6431', 'J512', 'J6356', 'L2316', 'L621', 'S4563', 'S65')
  )
  AND (
    ci.note IN ('(archive footage)', '(associate producer)', '(creative producer)', '(line producer)', '(producer)', '(voice) (uncredited)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'composer', 'producer', 'writer')
  )
  AND (
    it1.id IN ('37')
  )
