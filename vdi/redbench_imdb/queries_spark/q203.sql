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
    n.name_pcode_nf IN ('C6212', 'D5421', 'D6412', 'E5462', 'E645', 'F6521', 'G6532', 'J1361', 'J2165', 'J2354', 'J5326', 'K6261', 'M4245', 'N516', 'P4141', 'P4143', 'R246', 'R5342', 'S1235', 'S5165', 'S6356', 'T625')
  )
  AND (
    ci.note IN ('(caterer)', '(coordinating producer)', '(line producer)', '(production assistant)', '(script coordinator)', '(supervising producer)', '(written by)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'composer', 'director', 'editor', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('34')
  )
