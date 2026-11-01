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
    n.name_pcode_nf IN ('B2346', 'C63', 'E6423', 'F5362', 'J2612', 'J545', 'L5625', 'N2513', 'R1521', 'R523', 'S3541', 'S632', 'T6236', 'U4621')
  )
  AND (
    ci.note IN ('(assistant producer)', '(characters created by)', '(co-producer)', '(consultant writer)', '(producer)', '(uncredited)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'director', 'producer', 'production designer', 'writer')
  )
  AND (
    it1.id IN ('31')
  )
