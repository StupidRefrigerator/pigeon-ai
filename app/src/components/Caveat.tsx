import { LAYER_DATA } from '../infra-data'
import { useLayer } from '../layer'

const list = (names: string[]) => `${names.slice(0, -1).join(', ')} and ${names.at(-1)}`

/** The selected layer's known data gap, shown on each of its pages; nothing for a layer without one. */
export function Caveat() {
  const { id, unit } = useLayer()
  const u = LAYER_DATA[id].tracking.undercount
  if (!u) return null
  return (
    <p className="caveat" role="note">
      <strong>Data gap:</strong> {`Council records are thin in the west. ${list(u.councils)} have ${u.recorded} ${unit.many} on record where the model predicts ${u.predicted}, so predictions there are less checked, and some of the ${u.listed} suggested places there may already have one.`}
    </p>
  )
}
