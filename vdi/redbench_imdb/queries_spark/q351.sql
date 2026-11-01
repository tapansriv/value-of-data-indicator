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
    n.gender IN ('f') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('A6352', 'D132', 'D24', 'E3252', 'E4513', 'J5253', 'J5456', 'K4242', 'L2325', 'R2636', 'R5235', 'S1532', 'S2541', 'T5125', 'U4621')
  )
  AND (
    ci.note IN ('(characters)', '(co-producer)', '(consulting producer)', '(field producer)', '(producer)', '(production assistant) (as Keila Marie Celso)', '(production assistant)', '(script continuity)', '(script editor)', '(storylines)', '(supervising producer)', '(technical director)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('cinematographer', 'director', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('22')
  )
