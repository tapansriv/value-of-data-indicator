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
    n.name_pcode_nf IN ('C6252', 'F3624', 'J2143', 'J2325', 'J5235', 'M2351', 'M652', 'P142', 'T6365')
    OR n.name_pcode_nf IS NULL
  )
  AND (
    ci.note IN ('(adr voice director)', '(associate head writer) (as Jim Houghton)', '(executive producer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'miscellaneous crew', 'producer', 'production designer', 'writer')
  )
  AND (
    it1.id IN ('22')
  )
