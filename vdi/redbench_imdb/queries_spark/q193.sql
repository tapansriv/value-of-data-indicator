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
    n.gender IN ('f')
  )
  AND (
    n.name_pcode_nf IN ('A5162', 'C5165', 'D5263', 'E2152', 'F5152', 'G5415', 'G5453', 'J6135', 'L465', 'N6', 'P3626', 'R2343', 'S2526', 'S5252', 'Z426')
  )
  AND (
    ci.note IN ('(co-executive producer) (as Suzy Mamann Greenberg)', '(voice)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'editor', 'producer')
  )
  AND (
    it1.id IN ('31')
  )
