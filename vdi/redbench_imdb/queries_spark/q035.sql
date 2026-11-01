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
    n.name_pcode_nf IN ('A6216', 'B4653', 'B6153', 'B6234', 'B6525', 'C435', 'C565', 'C6213', 'D51', 'E5413', 'G1621', 'G4252', 'G4514', 'K54', 'L5142', 'M3214', 'M4245', 'N6523', 'P4142', 'P6165', 'S3243', 'S5256')
  )
  AND (
    ci.note IN ('(as Brigitte Walbrunn)', '(executive producer)', '(uncredited)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'director', 'producer')
  )
  AND (
    it1.id IN ('22')
  )
