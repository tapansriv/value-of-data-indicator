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
    n.name_pcode_nf IN ('A3531', 'A4123', 'A5352', 'A5361', 'A5624', 'B6516', 'C6216', 'D1321', 'G6241', 'J1242', 'J531', 'K5453', 'O4163', 'P1516', 'P43', 'P4524', 'R1652', 'R2626', 'S5262', 'T6254')
  )
  AND (
    ci.note IN ('(executive producer)', '(producer)', '(production assistant)', '(talent coordinator)', '(uncredited)', '(writer)', '(written by)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'cinematographer', 'director', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('22')
  )
